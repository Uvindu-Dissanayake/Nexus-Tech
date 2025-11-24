# billing_receipt.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
from datetime import datetime
import csv
import os

-
DB_FILE = "shop.db"
TAX_RATE = 0.15          
LOYALTY_PER_DOLLAR = 0.1  


# Ensure required tables for transactions exist
def init_billing_tables():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")
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
            subtotal REAL,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE
        )
    """)
    # customers table is optional; if present, loyalty updates will work
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            loyalty_points INTEGER DEFAULT 0
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

# ---------- Simple Billing GUI ----------
class BillingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Billing & Receipt - POS")
        self.geometry("1000x600")

        init_billing_tables()

        # in-memory cart: list of dicts {product_id, name, price, qty, subtotal}
        self.cart = []
        self.selected_customer = None  # optional (id, name)
        self.staff = "cashier"

        # layout: left product area, right cart/checkout
        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        right = ttk.Frame(self, width=360)
        right.pack(side="right", fill="y", padx=6, pady=6)

        ProductSelection(left, self).pack(fill="both", expand=True)
        CartFrame(right, self).pack(fill="y", expand=False)

# ---------- Product Selection Panel ----------
class ProductSelection(ttk.Frame):
    def __init__(self, parent, app: BillingApp):
        super().__init__(parent)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x", pady=4)
        ttk.Label(top, text="Search product (name or id):").pack(side="left")
        self.q = tk.StringVar()
        ttk.Entry(top, textvariable=self.q, width=40).pack(side="left", padx=6)
        ttk.Button(top, text="Search", command=self.search).pack(side="left")
        ttk.Button(top, text="Show All", command=self.load_all).pack(side="left", padx=4)

        # tree
        cols = ("id", "name", "category", "price", "stock")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        for c in cols:
            self.tree.heading(c, text=c.title())
            self.tree.column(c, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=4, pady=6)

        right_controls = ttk.Frame(self)
        right_controls.pack(fill="x", padx=4)

        ttk.Label(right_controls, text="Quantity:").pack(side="left")
        self.qty_var = tk.IntVar(value=1)
        ttk.Spinbox(right_controls, from_=1, to=999, textvariable=self.qty_var, width=6).pack(side="left", padx=6)
        ttk.Button(right_controls, text="Add to Cart", command=self.add_selected).pack(side="left")
        ttk.Button(right_controls, text="Quick ID", command=self.quick_by_id).pack(side="left", padx=6)

        self.load_all()

    def load_all(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = db_fetch("SELECT id, name, category, price, stock FROM products ORDER BY id")
        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["name"], r["category"] or "", f"{r['price']:.2f}" if r['price'] is not None else "", r["stock"] if r["stock"] is not None else ""))

    def search(self):
        term = self.q.get().strip()
        if not term:
            self.load_all(); return
        if term.isdigit():
            rows = db_fetch("SELECT id, name, category, price, stock FROM products WHERE id=?", (int(term),))
        else:
            rows = db_fetch("SELECT id, name, category, price, stock FROM products WHERE name LIKE ? OR category LIKE ?", (f"%{term}%", f"%{term}%"))
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["name"], r["category"] or "", f"{r['price']:.2f}" if r['price'] is not None else "", r["stock"] if r["stock"] is not None else ""))

    def add_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a product to add.")
            return
        vals = self.tree.item(sel[0])["values"]
        pid = int(vals[0]); name = vals[1]; price = float(vals[3]) if vals[3] else 0.0
        stock = None
        try:
            stock = int(vals[4]) if vals[4] != "" else None
        except:
            stock = None
        qty = int(self.qty_var.get() or 1)
        if stock is not None and qty > stock:
            messagebox.showwarning("Stock", f"Only {stock} available.")
            return
        # merge to cart
        for item in self.app.cart:
            if item["product_id"] == pid:
                item["qty"] += qty
                item["subtotal"] = item["qty"] * item["price"]
                break
        else:
            self.app.cart.append({"product_id": pid, "name": name, "price": price, "qty": qty, "subtotal": price * qty})
        # notify cart frame to refresh
        for child in self.master.winfo_children():
            if isinstance(child, CartFrame):
                child.refresh()
        # or simply call globally:
        for w in self.app.winfo_children():
            pass

    def quick_by_id(self):
        pid = simpledialog.askinteger("Product ID", "Enter product ID")
        if not pid: return
        row = db_fetch("SELECT id, name, price, stock FROM products WHERE id=?", (pid,))
        if not row:
            messagebox.showerror("Not found", "Product ID not found.")
            return
        r = row[0]
        name = r["name"]; price = r["price"] or 0.0; stock = r["stock"]
        qty = simpledialog.askinteger("Quantity", f"Quantity for {name}", initialvalue=1, minvalue=1)
        if not qty: return
        if stock is not None and qty > stock:
            messagebox.showwarning("Stock", f"Only {stock} available.")
            return
        # add
        for item in self.app.cart:
            if item["product_id"] == pid:
                item["qty"] += qty
                item["subtotal"] = item["qty"] * item["price"]
                break
        else:
            self.app.cart.append({"product_id": pid, "name": name, "price": price, "qty": qty, "subtotal": price * qty})
        for child in self.master.winfo_children():
            if isinstance(child, CartFrame):
                child.refresh()

# ---------- Cart & Checkout ----------
class CartFrame(ttk.Frame):
    def __init__(self, parent, app: BillingApp):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Cart & Checkout", font=("Helvetica", 12, "bold")).pack(pady=6)

        cols = ("product_id","name","qty","price","subtotal")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c.title())
            self.tree.column(c, anchor="center")
        self.tree.pack(fill="both", padx=6, pady=6)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=6)
        ttk.Button(btns, text="Remove", command=self.remove).pack(side="left", padx=2)
        ttk.Button(btns, text="Edit Qty", command=self.edit_qty).pack(side="left", padx=2)
        ttk.Button(btns, text="Clear", command=self.clear_cart).pack(side="left", padx=2)

        # discount, payment
        pframe = ttk.Frame(self)
        pframe.pack(fill="x", padx=6, pady=8)
        ttk.Label(pframe, text="Discount %").grid(row=0,column=0)
        self.disc_pct = tk.DoubleVar(value=0.0)
        ttk.Entry(pframe, textvariable=self.disc_pct, width=8).grid(row=0,column=1,padx=4)
        ttk.Label(pframe, text="Discount $").grid(row=0,column=2)
        self.disc_amt = tk.DoubleVar(value=0.0)
        ttk.Entry(pframe, textvariable=self.disc_amt, width=8).grid(row=0,column=3,padx=4)
        ttk.Label(pframe, text="Payment").grid(row=1,column=0)
        self.pay_method = tk.StringVar(value="Cash")
        ttk.Combobox(pframe, textvariable=self.pay_method, values=["Cash","Card","Other"], width=10).grid(row=1,column=1,padx=4)

        # totals
        self.sub_label = ttk.Label(self, text="Subtotal: $0.00")
        self.sub_label.pack(anchor="w", padx=6)
        self.tax_label = ttk.Label(self, text=f"Tax ({TAX_RATE*100:.0f}%): $0.00")
        self.tax_label.pack(anchor="w", padx=6)
        self.disc_label = ttk.Label(self, text="Discount: $0.00")
        self.disc_label.pack(anchor="w", padx=6)
        self.total_label = ttk.Label(self, text="Grand Total: $0.00", font=("Helvetica",11,"bold"))
        self.total_label.pack(anchor="w", padx=6, pady=6)

        ttk.Button(self, text="Recalc", command=self.refresh).pack(side="left", padx=6)
        ttk.Button(self, text="Checkout", command=self.checkout).pack(side="right", padx=6)

        self.refresh()

    def refresh(self):
        # refresh tree
        for i in self.tree.get_children(): self.tree.delete(i)
        for item in self.app.cart:
            self.tree.insert("", "end", values=(item["product_id"], item["name"], item["qty"], f"{item['price']:.2f}", f"{item['subtotal']:.2f}"))
        totals = self.compute_totals()
        self.sub_label.config(text=f"Subtotal: ${totals['subtotal']:.2f}")
        self.tax_label.config(text=f"Tax ({TAX_RATE*100:.0f}%): ${totals['tax']:.2f}")
        self.disc_label.config(text=f"Discount: ${totals['discount']:.2f}")
        self.total_label.config(text=f"Grand Total: ${totals['grand_total']:.2f}")

    def compute_totals(self):
        subtotal = sum(i["subtotal"] for i in self.app.cart)
        tax = subtotal * TAX_RATE
        pct = float(self.disc_pct.get() or 0.0)
        amt = float(self.disc_amt.get() or 0.0)
        disc = subtotal * (pct/100.0) + amt
        grand = max(0.0, subtotal + tax - disc)
        return {"subtotal": subtotal, "tax": tax, "discount": disc, "grand_total": grand}

    def remove(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an item to remove.")
            return
        pid = int(self.tree.item(sel[0])["values"][0])
        self.app.cart = [it for it in self.app.cart if it["product_id"] != pid]
        self.refresh()

    def edit_qty(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select item.")
            return
        pid = int(self.tree.item(sel[0])["values"][0])
        item = next((it for it in self.app.cart if it["product_id"]==pid), None)
        if not item: return
        newq = simpledialog.askinteger("Qty", "New quantity", initialvalue=item["qty"], minvalue=1)
        if not newq: return
        # check stock
        row = db_fetch("SELECT stock FROM products WHERE id=?", (pid,))
        stock = row[0]["stock"] if row else None
        if stock is not None and newq > stock:
            messagebox.showwarning("Stock", f"Only {stock} available.")
            return
        item["qty"] = newq
        item["subtotal"] = item["qty"] * item["price"]
        self.refresh()

    def clear_cart(self):
        if not messagebox.askyesno("Confirm", "Clear cart?"): return
        self.app.cart.clear()
        self.refresh()

    def checkout(self):
        if not self.app.cart:
            messagebox.showwarning("Empty", "Cart is empty.")
            return
        totals = self.compute_totals()
        pay = self.pay_method.get() or "Cash"
        confirm = messagebox.askyesno("Confirm", f"Charge ${totals['grand_total']:.2f} via {pay}?")
        if not confirm: return

        # perform DB transaction
        invoice = generate_invoice_no()
        cust_id = self.app.selected_customer[0] if self.app.selected_customer else None
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.execute("PRAGMA foreign_keys = ON;")
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sales (invoice_no, customer_id, subtotal, tax, discount, grand_total, payment_method, staff)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice, cust_id, totals["subtotal"], totals["tax"], totals["discount"], totals["grand_total"], pay, self.app.staff))
            sale_id = cur.lastrowid

            # insert items and update stock
            for it in self.app.cart:
                cur.execute("""
                    INSERT INTO sales_items (sale_id, product_id, name, qty, price, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sale_id, it["product_id"], it["name"], it["qty"], it["price"], it["subtotal"]))
                # update stock
                cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (it["qty"], it["product_id"]))

            # update loyalty if customer exists
            if cust_id:
                earned = int(totals["grand_total"] * LOYALTY_PER_DOLLAR)
                cur.execute("UPDATE customers SET loyalty_points = COALESCE(loyalty_points,0) + ? WHERE id=?", (earned, cust_id))
            else:
                earned = 0

            conn.commit()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Failed", f"Checkout failed: {e}")
            conn.close()
            return
        conn.close()

        # show receipt
        self.show_receipt_dialog(invoice, sale_id, totals, pay, earned)
        # clear cart
        self.app.cart.clear()
        self.disc_amt.set(0.0); self.disc_pct.set(0.0)
        self.refresh()

    def show_receipt_dialog(self, invoice_no, sale_id, totals, payment_method, loyalty_earned):
        rows = db_fetch("SELECT name, qty, price, subtotal FROM sales_items WHERE sale_id=?", (sale_id,))
        win = tk.Toplevel(self)
        win.title(f"Receipt {invoice_no}")
        txt = tk.Text(win, width=60, height=30)
        txt.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = ttk.Scrollbar(win, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.config(yscrollcommand=sb.set)

        lines = []
        lines.append("===== NEXUS TECH SHOP =====")
        lines.append(f"Invoice: {invoice_no}")
        lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.app.selected_customer:
            lines.append(f"Customer: {self.app.selected_customer[1]} (ID:{self.app.selected_customer[0]})")
        lines.append(f"Staff: {self.app.staff}")
        lines.append("-"*40)
        lines.append("{:30s}{:>5s}{:>10s}{:>10s}".format("Item","Qty","Price","Sub"))
        lines.append("-"*40)
        for r in rows:
            n, q, p, s = r["name"], r["qty"], r["price"], r["subtotal"]
            lines.append("{:30.30s}{:>5d}{:>10.2f}{:>10.2f}".format(n,q,p,s))
        lines.append("-"*40)
        lines.append(f"Subtotal: ${totals['subtotal']:.2f}")
        lines.append(f"Tax ({TAX_RATE*100:.0f}%): ${totals['tax']:.2f}")
        lines.append(f"Discount: -${totals['discount']:.2f}")
        lines.append(f"Grand Total: ${totals['grand_total']:.2f}")
        lines.append(f"Payment: {payment_method}")
        if loyalty_earned:
            lines.append(f"Loyalty points earned: {loyalty_earned}")
        lines.append("Thank you for shopping!")
        lines.append("===========================")

        txt.insert("1.0", "\n".join(lines))
        txt.config(state="disabled")

        btnf = ttk.Frame(win)
        btnf.pack(fill="x", padx=6, pady=6)
        ttk.Button(btnf, text="Save .txt", command=lambda: self.save_receipt(invoice_no, "\n".join(lines))).pack(side="left")
        ttk.Button(btnf, text="Close", command=win.destroy).pack(side="right")

    def save_receipt(self, invoice, content):
        fn = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"{invoice}.txt")
        if not fn:
            return
        with open(fn, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Saved", f"Receipt saved to {fn}")

if __name__ == "__main__":
    # Ensure DB exists and products table probably created by Code 2; create billing tables now.
    if not os.path.exists(DB_FILE):
        # If shop.db doesn't exist, create it with products table skeleton (so app still runs)
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
        conn.commit()
        conn.close()
    init_billing_tables()
    app = BillingApp()
    app.mainloop()
