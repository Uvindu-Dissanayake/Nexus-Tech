

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk   # << YOU NEED PILLOW INSTALLED
import sqlite3
from datetime import datetime
import os

DB_FILE = "shop.db"
TAX_RATE = 0.15
LOYALTY_PER_DOLLAR = 0.1


# -----------------------------------------------------------
# INITIALISE TABLES
# -----------------------------------------------------------
def init_billing_tables():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price REAL,
            stock INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            loyalty_points INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE,
            customer_id INTEGER,
            subtotal REAL,
            tax REAL,
            discount REAL,
            grand_total REAL,
            payment_method TEXT,
            card_type TEXT,
            staff TEXT,
            timestamp TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sales_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            name TEXT,
            qty INTEGER,
            price REAL,
            subtotal REAL
        )
    """)

    conn.commit()
    conn.close()


def db_fetch(sql, params=()):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def db_exec(sql, params=()):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()


def generate_invoice_no():
    return "INV" + datetime.now().strftime("%Y%m%d%H%M%S")


# -----------------------------------------------------------
# BILLING APPLICATION MAIN WINDOW
# -----------------------------------------------------------
class BillingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Billing & Receipt - POS System")
        self.geometry("1100x650")
        self.resizable(False, False)

        init_billing_tables()

        self.cart = []
        self.selected_customer = None
        self.staff = "Cashier"

        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(self, width=350)
        right.pack(side="right", fill="y")

        ProductSelection(left, self).pack(fill="both", expand=True)
        CartFrame(right, self).pack(fill="y")


# -----------------------------------------------------------
# PRODUCT SELECTION PANEL
# -----------------------------------------------------------
class ProductSelection(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x", pady=5)

        ttk.Label(top, text="Search Product:").pack(side="left")
        self.q = tk.StringVar()
        ttk.Entry(top, textvariable=self.q, width=40).pack(side="left", padx=5)
        ttk.Button(top, text="Search", command=self.search).pack(side="left")
        ttk.Button(top, text="Show All", command=self.load_all).pack(side="left", padx=5)

        cols = ("id","name","category","price","stock")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=22)
        for col in cols:
            self.tree.heading(col, text=col.title())
        self.tree.pack(fill="both", expand=True, pady=10)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x")

        ttk.Label(bottom, text="Qty: ").pack(side="left")
        self.qty = tk.IntVar(value=1)
        ttk.Entry(bottom, textvariable=self.qty, width=5).pack(side="left", padx=5)

        ttk.Button(bottom, text="Add", command=self.add_selected).pack(side="left")
        ttk.Button(bottom, text="Quick ID", command=self.quick_add).pack(side="left")

        self.load_all()

    def load_all(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = db_fetch("SELECT * FROM products ORDER BY id")
        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["name"], r["category"], r["price"], r["stock"]))

    def search(self):
        term = self.q.get()
        for i in self.tree.get_children():
            self.tree.delete(i)

        if term.isdigit():
            rows = db_fetch("SELECT * FROM products WHERE id=?", (term,))
        else:
            rows = db_fetch("SELECT * FROM products WHERE name LIKE ?", (f"%{term}%",))

        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["name"], r["category"], r["price"], r["stock"]))

    def add_selected(self):
        try:
            sel = self.tree.item(self.tree.selection()[0])["values"]
        except:
            messagebox.showwarning("Select", "Please select a product.")
            return

        pid, name, cat, price, stock = sel
        qty = self.qty.get()

        if qty > stock:
            messagebox.showerror("Stock Error", f"Only {stock} available.")
            return

        for item in self.app.cart:
            if item["id"] == pid:
                item["qty"] += qty
                item["subtotal"] = item["qty"] * item["price"]
                break
        else:
            self.app.cart.append({
                "id": pid,
                "name": name,
                "price": price,
                "qty": qty,
                "subtotal": qty * price
            })

        self.master.master.children["!cartframe"].refresh()

    def quick_add(self):
        pid = simpledialog.askinteger("Product ID", "Enter product ID:")
        if not pid:
            return

        row = db_fetch("SELECT * FROM products WHERE id=?", (pid,))
        if not row:
            messagebox.showerror("Error", "Product not found.")
            return

        product = row[0]
        qty = simpledialog.askinteger("Quantity", f"Qty for {product['name']}:", initialvalue=1)

        if qty > product["stock"]:
            messagebox.showerror("Stock", f"Only {product['stock']} available.")
            return

        self.app.cart.append({
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "qty": qty,
            "subtotal": qty * product["price"]
        })

        self.master.master.children["!cartframe"].refresh()


# -----------------------------------------------------------
# CART + CHECKOUT PANEL (PAYMENT LOGOS INCLUDED)
# -----------------------------------------------------------
class CartFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="CART", font=("Arial", 14, "bold")).pack(pady=5)

        cols = ("id","name","qty","price","subtotal")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for col in cols:
            self.tree.heading(col, text=col.title())
        self.tree.pack(fill="x", pady=5)

        b = ttk.Frame(self)
        b.pack(pady=5)
        ttk.Button(b, text="Remove", command=self.remove).pack(side="left", padx=4)
        ttk.Button(b, text="Clear", command=self.clear).pack(side="left", padx=4)

        # DISCOUNT + PAYMENT
        frame = ttk.LabelFrame(self, text="Payment & Discounts")
        frame.pack(fill="x", pady=10)

        ttk.Label(frame, text="Discount %").grid(row=0, column=0)
        self.discP = tk.DoubleVar(value=0)
        ttk.Entry(frame, textvariable=self.discP, width=7).grid(row=0, column=1, padx=5)

        ttk.Label(frame, text="Discount $").grid(row=0, column=2)
        self.discA = tk.DoubleVar(value=0)
        ttk.Entry(frame, textvariable=self.discA, width=7).grid(row=0, column=3, padx=5)

        # -------------------------------
        # PAYMENT METHOD DROPDOWN
        # -------------------------------
        ttk.Label(frame, text="Payment Method").grid(row=1, column=0, pady=10)

        self.pay_method = tk.StringVar(value="Cash")
        self.payment_box = ttk.Combobox(
            frame,
            textvariable=self.pay_method,
            values=["Cash", "Card", "PayWave", "Online Bank Transfer"],
            width=18
        )
        self.payment_box.grid(row=1, column=1)

        self.payment_box.bind("<<ComboboxSelected>>", self.update_payment_ui)

        # CARD TYPE DROPDOWN (Hidden unless "Card")
        ttk.Label(frame, text="Card Type").grid(row=1, column=2)
        self.card_type = tk.StringVar(value="Visa")

        self.card_box = ttk.Combobox(
            frame,
            textvariable=self.card_type,
            values=["Visa", "Debit", "Credit"],
            state="disabled",
            width=12
        )
        self.card_box.grid(row=1, column=3)

        # ---------------------------------------------------------
        # ==== PUT YOUR PAYMENT LOGOS IN THIS SECTION ====
        #
        # REQUIRED FILES (PNG) → must be in same directory:
        #   cash.png
        #   visa.png
        #   debit.png
        #   credit.png
        #   paywave.png
        #   bank.png
        # ---------------------------------------------------------

        def load_icon(name):
            try:
                img = Image.open(name).resize((60, 40))
                return ImageTk.PhotoImage(img)
            except:
                return None

        self.icons = {
            "Cash": load_icon("cash.png"),
            "Visa": load_icon("visa.png"),
            "Debit": load_icon("debit.png"),
            "Credit": load_icon("credit.png"),
            "PayWave": load_icon("paywave.png"),
            "Online Bank Transfer": load_icon("bank.png")
        }

        # Label to show payment icon
        self.icon_label = ttk.Label(frame)
        self.icon_label.grid(row=2, column=0, columnspan=4, pady=10)

        # -------------------------------
        # TOTALS
        # -------------------------------
        self.subT = ttk.Label(self, text="Subtotal: $0.00")
        self.subT.pack(anchor="w", padx=10)

        self.taxT = ttk.Label(self, text=f"Tax ({TAX_RATE*100:.0f}%): $0.00")
        self.taxT.pack(anchor="w", padx=10)

        self.disT = ttk.Label(self, text="Discount: $0.00")
        self.disT.pack(anchor="w", padx=10)

        self.grandT = ttk.Label(self, text="Grand Total: $0.00", font=("Arial", 11, "bold"))
        self.grandT.pack(anchor="w", padx=10, pady=5)

        ttk.Button(self, text="Checkout", command=self.checkout).pack(pady=10)

        self.refresh()


    # -------------------------------
    # PAYMENT UI UPDATE
    # -------------------------------
    def update_payment_ui(self, event=None):
        method = self.pay_method.get()

        # Show card dropdown only for "Card"
        if method == "Card":
            self.card_box.config(state="normal")
            icon = self.icons.get("Visa")
        else:
            self.card_box.config(state="disabled")
            icon = self.icons.get(method)

        # Display logo
        if icon:
            self.icon_label.config(image=icon)
            self.icon_label.image = icon
        else:
            self.icon_label.config(image="", text="No Icon Found")


    # -------------------------------
    # CART FUNCTIONS
    # -------------------------------
    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        subtotal = 0
        for item in self.app.cart:
            self.tree.insert("", "end", values=(item["id"], item["name"], item["qty"], item["price"], item["subtotal"]))
            subtotal += item["subtotal"]

        tax = subtotal * TAX_RATE
        disc = subtotal * (self.discP.get()/100) + self.discA.get()
        grand = subtotal + tax - disc

        self.subT.config(text=f"Subtotal: ${subtotal:.2f}")
        self.taxT.config(text=f"Tax ({TAX_RATE*100:.0f}%): ${tax:.2f}")
        self.disT.config(text=f"Discount: ${disc:.2f}")
        self.grandT.config(text=f"Grand Total: ${grand:.2f}")

    def remove(self):
        try:
            pid = self.tree.item(self.tree.selection()[0])["values"][0]
        except:
            return

        self.app.cart = [i for i in self.app.cart if i["id"] != pid]
        self.refresh()

    def clear(self):
        self.app.cart.clear()
        self.refresh()


    # -------------------------------
    # CHECKOUT
    # -------------------------------
    def checkout(self):
        if not self.app.cart:
            messagebox.showerror("Empty", "Nothing in cart.")
            return

        subtotal = sum(i["subtotal"] for i in self.app.cart)
        tax = subtotal * TAX_RATE
        disc = subtotal * (self.discP.get()/100) + self.discA.get()
        grand = subtotal + tax - disc

        pay_method = self.pay_method.get()
        card_type = self.card_type.get() if pay_method == "Card" else None

        confirm = messagebox.askyesno("Confirm", f"Pay ${grand:.2f} using {pay_method}?")
        if not confirm:
            return

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        invoice = generate_invoice_no()
        cur.execute("""
            INSERT INTO sales (invoice_no, subtotal, tax, discount, grand_total, payment_method, card_type, staff)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (invoice, subtotal, tax, disc, grand, pay_method, card_type, self.app.staff))

        sale_id = cur.lastrowid

        # Insert items
        for it in self.app.cart:
            cur.execute("""
                INSERT INTO sales_items (sale_id, product_id, name, qty, price, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sale_id, it["id"], it["name"], it["qty"], it["price"], it["subtotal"]))

            # reduce stock
            cur.execute("UPDATE products SET stock = stock - ? WHERE id=?", (it["qty"], it["id"]))

        conn.commit()
        conn.close()

        messagebox.showinfo("Success", f"Payment Successful!\nInvoice: {invoice}")

        self.app.cart.clear()
        self.refresh()


# -----------------------------------------------------------
# RUN APP
# -----------------------------------------------------------
if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        init_billing_tables()
    app = BillingApp()
    app.mainloop()
