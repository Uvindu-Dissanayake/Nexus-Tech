#!/usr/bin/env python3
"""
POSApp - full billing system with:
 - new payment methods including Card + card subtype dropdown
 - barcode scanner support (keyboard wedge)
 - printable PDF receipts (requires reportlab)
 - product quick manager, customers, sales logging, loyalty
Save as pos_app.py and run with Python 3.x
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import sqlite3
from datetime import datetime
import os
import csv
import sys

# Try import for PDF generation
HAS_REPORTLAB = True
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdfcanvas
except Exception:
    HAS_REPORTLAB = False

# ------------ Config ------------
DB_FILE = "shop.db"        # same DB used by your other code
TAX_RATE = 0.15            # 15% GST - change if needed
LOYALTY_PER_DOLLAR = 0.1   # 0.1 point per $1 (=> 1 point per $10)
# ---------------------------------


# ---------- DB helpers ----------
def db_connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def db_query(sql, params=(), fetch=False):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(sql, params)
    res = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

def ensure_column_exists(table, column, col_def):
    """Add a column if missing (sqlite allows ALTER TABLE ADD COLUMN)."""
    conn = db_connect()
    cur = conn.cursor()
    # check columns
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r['name'] for r in cur.fetchall()]
    if column not in cols:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
            conn.commit()
        except Exception:
            # ignore - defensive
            pass
    conn.close()


def init_db():
    """Create missing tables required for POS (keeps existing products table)."""
    conn = db_connect()
    c = conn.cursor()

    # products table may exist from "Code2". Create minimal if absent.
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price REAL DEFAULT 0.0,
            stock INTEGER DEFAULT 0,
            barcode TEXT
        )
    """)

    # customers table (optional for customer-linked sales)
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            loyalty_points INTEGER DEFAULT 0
        )
    """)

    # sales table (header)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE,
            customer_id INTEGER,
            total REAL,
            tax REAL,
            discount REAL,
            grand_total REAL,
            payment_method TEXT,
            payment_details TEXT,  -- extra (card type etc)
            staff TEXT,
            timestamp TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
        )
    """)

    # sales_items table (line items)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sales_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            name TEXT,
            qty INTEGER,
            price REAL,
            subtotal REAL,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    """)

    conn.commit()
    conn.close()

    # ensure barcode column exists on products (safe add)
    ensure_column_exists("products", "barcode", "TEXT")


# ---------- Utilities ----------
def generate_invoice_no():
    t = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"INV{t}"


# ---------- Main Application ----------
class POSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("POS - Full Billing System")
        self.geometry("1150x720")

        init_db()  # ensure tables exist

        self.cart = []  # list of dicts: {product_id, name, price, qty, subtotal}
        self.selected_customer = None  # (id, name) or None
        self.staff_name = "cashier"    # change or prompt for staff login in future

        # Layout frames
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(main, width=420)
        right.pack(side="right", fill="y")

        # Product search & list
        self.product_search_frame = ProductSearchFrame(left, self)
        self.product_search_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Cart & Checkout
        self.cart_frame = CartCheckoutFrame(right, self)
        self.cart_frame.pack(fill="y", expand=False, padx=4, pady=4)

        # Bottom: quick actions
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=8, pady=4)
        ttk.Button(bottom, text="Export Sales CSV", command=self.export_sales_csv).pack(side="left", padx=4)
        ttk.Button(bottom, text="Open Product Manager", command=self.open_product_manager).pack(side="left", padx=4)
        ttk.Button(bottom, text="Quit", command=self.destroy).pack(side="right", padx=4)

        # Focus the hidden scan entry so keyboard-wedge barcode scanners work
        self.after(200, self.product_search_frame.focus_scanner_entry)

    def add_to_cart(self, product_id, name, price, qty):
        # Merge if already present
        for item in self.cart:
            if item['product_id'] == product_id:
                item['qty'] += qty
                item['subtotal'] = item['qty'] * item['price']
                self.cart_frame.refresh_cart()
                return
        item = {'product_id': product_id, 'name': name, 'price': price, 'qty': qty, 'subtotal': price * qty}
        self.cart.append(item)
        self.cart_frame.refresh_cart()

    def remove_from_cart(self, product_id):
        self.cart = [i for i in self.cart if i['product_id'] != product_id]
        self.cart_frame.refresh_cart()

    def clear_cart(self):
        self.cart.clear()
        self.selected_customer = None
        self.cart_frame.refresh_cart()

    def compute_totals(self, discount_percent=0.0, discount_amount=0.0):
        subtotal = sum(i['subtotal'] for i in self.cart)
        tax = subtotal * TAX_RATE
        discount_from_percent = subtotal * (discount_percent / 100.0)
        discount = discount_from_percent + discount_amount
        grand_total = max(0.0, subtotal + tax - discount)
        return {
            'subtotal': subtotal,
            'tax': tax,
            'discount': discount,
            'grand_total': grand_total
        }

    def checkout(self, payment_method, discount_percent=0.0, discount_amount=0.0, payment_details=None):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Cart is empty.")
            return False

        totals = self.compute_totals(discount_percent, discount_amount)
        invoice_no = generate_invoice_no()
        cust_id = self.selected_customer[0] if self.selected_customer else None
        staff = self.staff_name

        # Begin transaction
        conn = db_connect()
        cur = conn.cursor()
        try:
            # insert sale header
            cur.execute("""
                INSERT INTO sales (invoice_no, customer_id, total, tax, discount, grand_total, payment_method, payment_details, staff)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_no, cust_id, totals['subtotal'], totals['tax'], totals['discount'], totals['grand_total'], payment_method, payment_details, staff))
            sale_id = cur.lastrowid

            # insert sale items and update product stock
            for item in self.cart:
                cur.execute("""
                    INSERT INTO sales_items (sale_id, product_id, name, qty, price, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sale_id, item['product_id'], item['name'], item['qty'], item['price'], item['subtotal']))

                # decrement stock (if product exists)
                cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item['qty'], item['product_id']))

            # update customer loyalty if applicable
            if cust_id:
                loyalty_points_earned = int(totals['grand_total'] * LOYALTY_PER_DOLLAR)
                cur.execute("UPDATE customers SET loyalty_points = COALESCE(loyalty_points,0) + ? WHERE id = ?", (loyalty_points_earned, cust_id))
                earned = loyalty_points_earned
            else:
                earned = 0

            conn.commit()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Checkout Error", f"Failed to complete sale: {e}")
            conn.close()
            return False

        conn.close()

        # Show receipt and clear cart
        self.show_receipt(invoice_no, sale_id, totals, payment_method, staff, earned, payment_details)
        self.clear_cart()
        return True

    def show_receipt(self, invoice_no, sale_id, totals, payment_method, staff, loyalty_earned, payment_details=None):
        # Fetch sale items to display exact saved data
        rows = db_query("SELECT name, qty, price, subtotal FROM sales_items WHERE sale_id=?", (sale_id,), fetch=True) or []
        receipt_win = tk.Toplevel(self)
        receipt_win.title(f"Receipt - {invoice_no}")
        receipt_win.geometry("600x600")
        receipt_text = tk.Text(receipt_win, width=80, height=30, wrap="none")
        receipt_text.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        scrollbar = ttk.Scrollbar(receipt_win, orient="vertical", command=receipt_text.yview)
        scrollbar.pack(side="right", fill="y")
        receipt_text.config(yscrollcommand=scrollbar.set)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        lines.append("=== NEXUS TECH SHOP ===")
        lines.append(f"Invoice: {invoice_no}")
        lines.append(f"Date: {now}")
        if self.selected_customer:
            lines.append(f"Customer: {self.selected_customer[1]} (ID:{self.selected_customer[0]})")
        lines.append(f"Staff: {staff}")
        lines.append("-"*48)
        lines.append(f"{'Item':30} {'Qty':>3} {'Price':>8} {'Sub':>9}")
        lines.append("-"*48)
        for r in rows:
            name, qty, price, sub = r
            lines.append(f"{name[:30]:30} {qty:>3} {price:>8.2f} {sub:>9.2f}")
        lines.append("-"*48)
        lines.append(f"Subtotal: ${totals['subtotal']:.2f}")
        lines.append(f"Tax ({TAX_RATE*100:.0f}%): ${totals['tax']:.2f}")
        lines.append(f"Discount: -${totals['discount']:.2f}")
        lines.append(f"Grand Total: ${totals['grand_total']:.2f}")
        lines.append(f"Payment: {payment_method} {('('+str(payment_details)+')') if payment_details else ''}")
        lines.append("-"*48)
        if loyalty_earned:
            lines.append(f"Loyalty points earned: {loyalty_earned}")
        lines.append("Thank you for shopping with us!")
        lines.append("=== Powered by POSApp ===")

        content = "\n".join(lines)
        receipt_text.insert("1.0", content)
        receipt_text.config(state="disabled")

        # Save receipt buttons
        btn_frame = ttk.Frame(receipt_win)
        btn_frame.pack(fill="x", padx=6, pady=6)
        ttk.Button(btn_frame, text="Save Receipt (.txt)", command=lambda: self.save_receipt_text(invoice_no, content)).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Save Receipt (.pdf)", command=lambda: self.save_receipt_pdf(invoice_no, lines)).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Close", command=receipt_win.destroy).pack(side="right", padx=4)

    def save_receipt_text(self, invoice_no, content):
        fn = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"{invoice_no}.txt")
        if not fn:
            return
        with open(fn, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Saved", f"Receipt saved to {fn}")

    def save_receipt_pdf(self, invoice_no, lines):
        if not HAS_REPORTLAB:
            messagebox.showerror("PDF Not Available", "PDF generation requires the 'reportlab' package.\nInstall with: pip install reportlab")
            return
        fn = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{invoice_no}.pdf")
        if not fn:
            return
        try:
            c = pdfcanvas.Canvas(fn, pagesize=A4)
            width, height = A4
            x = 40
            y = height - 40
            line_height = 14
            c.setFont("Courier", 10)
            for line in lines:
                # wrap long lines simply
                if y < 40:
                    c.showPage()
                    y = height - 40
                    c.setFont("Courier", 10)
                c.drawString(x, y, line)
                y -= line_height
            c.save()
            messagebox.showinfo("Saved", f"PDF receipt saved to {fn}")
        except Exception as e:
            messagebox.showerror("PDF Error", f"Failed to save PDF: {e}")

    def export_sales_csv(self):
        rows = db_query("""
            SELECT s.invoice_no, s.timestamp, s.grand_total, s.payment_method, s.payment_details, c.name as customer
            FROM sales s
            LEFT JOIN customers c ON c.id = s.customer_id
            ORDER BY s.timestamp DESC
        """, fetch=True) or []
        if not rows:
            messagebox.showinfo("No Data", "No sales to export.")
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="sales_export.csv")
        if not fn:
            return
        with open(fn, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Invoice", "Timestamp", "Grand Total", "Payment Method", "Payment Details", "Customer"])
            for r in rows:
                w.writerow([r['invoice_no'], r['timestamp'], f"{r['grand_total']:.2f}", r['payment_method'], r['payment_details'] or "", r['customer'] or ""])
        messagebox.showinfo("Exported", f"Sales exported to {fn}")

    def open_product_manager(self):
        pm = ProductQuickManager(self)
        pm.grab_set()


# ---------- Product Search Frame ----------
class ProductSearchFrame(ttk.Frame):
    def __init__(self, parent, app: POSApp):
        super().__init__(parent)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x", padx=4, pady=4)

        # Barcode scan entry (hidden but focused) - captures scanner keyboard wedge input
        ttk.Label(top, text="Scan Barcode / ID:").pack(side="left", padx=4)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(top, textvariable=self.scan_var, width=25)
        self.scan_entry.pack(side="left", padx=4)
        self.scan_entry.bind("<Return>", self.on_scan_enter)

        ttk.Label(top, text="Search Product:").pack(side="left", padx=8)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(top, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=4)
        ttk.Button(top, text="Search", command=self.search).pack(side="left", padx=4)
        ttk.Button(top, text="Show All", command=self.load_all).pack(side="left", padx=4)

        # Product list & category filter
        middle = ttk.Frame(self)
        middle.pack(fill="both", expand=True, padx=4, pady=4)

        left_list = ttk.Frame(middle)
        left_list.pack(side="left", fill="y")

        ttk.Label(left_list, text="Categories").pack(anchor="w")
        self.cat_listbox = tk.Listbox(left_list, height=15)
        self.cat_listbox.pack(fill="y", expand=False)
        self.cat_listbox.bind("<<ListboxSelect>>", self.on_cat_select)

        # populate categories from products table distinct values
        cats = db_query("SELECT DISTINCT category FROM products ORDER BY category", fetch=True) or []
        categories = [r[0] for r in cats if r[0]]
        categories.insert(0, "All")
        for c in categories:
            self.cat_listbox.insert("end", c)
        self.cat_listbox.selection_set(0)

        # products tree
        self.tree = ttk.Treeview(middle, columns=("id", "name", "price", "stock", "barcode"), show="headings")
        for col, w in (("id",60),("name",360),("price",100),("stock",80),("barcode",140)):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True, padx=6)

        # right side: add to cart controls
        right_controls = ttk.Frame(middle)
        right_controls.pack(side="right", fill="y", padx=6)

        ttk.Label(right_controls, text="Quantity").pack(pady=(4,0))
        self.qty_var = tk.IntVar(value=1)
        self.qty_spin = ttk.Spinbox(right_controls, from_=1, to=999, textvariable=self.qty_var, width=8)
        self.qty_spin.pack(pady=4)

        ttk.Button(right_controls, text="Add to Cart", command=self.add_selected_to_cart).pack(pady=6)
        ttk.Button(right_controls, text="Quick Scan (ID/Barcode)", command=self.quick_scan).pack(pady=6)
        ttk.Button(right_controls, text="Refresh Products", command=self.load_all).pack(pady=6)

        self.load_all()

    def focus_scanner_entry(self):
        try:
            self.scan_entry.focus_set()
        except Exception:
            pass

    def on_scan_enter(self, event=None):
        code = self.scan_var.get().strip()
        self.scan_var.set("")  # clear input
        if not code:
            return
        # Try lookup by barcode first
        row = db_query("SELECT id, name, price, stock FROM products WHERE barcode=? COLLATE NOCASE", (code,), fetch=True)
        if not row:
            # fallback numeric id?
            try:
                pid = int(code)
                row = db_query("SELECT id, name, price, stock FROM products WHERE id=?", (pid,), fetch=True)
            except Exception:
                row = None
        if not row:
            messagebox.showerror("Not found", f"Product with barcode/id '{code}' not found.")
            return
        r = row[0]
        name, price, stock = r['name'], r['price'], r['stock']
        qty = 1
        if stock is not None and qty > stock:
            messagebox.showwarning("Stock", f"Only {stock} available.")
            return
        self.app.add_to_cart(r['id'], name, price, qty)
        # bring focus back to scanner entry for next scan
        self.scan_entry.focus_set()

    def load_all(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = db_query("SELECT id, name, price, stock, COALESCE(barcode,'') as barcode FROM products ORDER BY id", fetch=True) or []
        for r in rows:
            pid, name, price, stock, barcode = r['id'], r['name'], r['price'], r['stock'], r['barcode']
            self.tree.insert("", "end", values=(pid, name, f"{price:.2f}", stock if stock is not None else "", barcode))

    def search(self):
        term = self.search_var.get().strip()
        if not term:
            self.load_all()
            return
        q = "SELECT id, name, price, stock, COALESCE(barcode,'') as barcode FROM products WHERE name LIKE ? OR category LIKE ? OR barcode LIKE ? ORDER BY id"
        rows = db_query(q, (f"%{term}%", f"%{term}%", f"%{term}%"), fetch=True) or []
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", "end", values=(r['id'], r['name'], f"{r['price']:.2f}", r['stock'] if r['stock'] is not None else "", r['barcode']))

    def on_cat_select(self, event=None):
        sel = self.cat_listbox.curselection()
        if not sel:
            return
        cat = self.cat_listbox.get(sel[0])
        for i in self.tree.get_children():
            self.tree.delete(i)
        if cat == "All":
            self.load_all()
            return
        rows = db_query("SELECT id, name, price, stock, COALESCE(barcode,'') as barcode FROM products WHERE category=? ORDER BY id", (cat,), fetch=True) or []
        for r in rows:
            self.tree.insert("", "end", values=(r['id'], r['name'], f"{r['price']:.2f}", r['stock'] if r['stock'] is not None else "", r['barcode']))

    def add_selected_to_cart(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a product to add.")
            return
        vals = self.tree.item(sel[0])['values']
        pid = int(vals[0])
        name = vals[1]
        price = float(vals[2])
        stock = vals[3] if vals[3] != "" else None
        try:
            stock = int(stock) if stock is not None else None
        except Exception:
            stock = None
        qty = int(self.qty_var.get() or 1)
        if stock is not None and qty > stock:
            messagebox.showwarning("Stock", f"Only {stock} available.")
            return
        self.app.add_to_cart(pid, name, price, qty)

    def quick_scan(self):
        pid = simpledialog.askstring("Scan", "Enter Product barcode or ID")
        if not pid:
            return
        code = pid.strip()
        # re-use scan flow
        self.scan_var.set(code)
        self.on_scan_enter()


# ---------- Cart & Checkout Frame ----------
class CartCheckoutFrame(ttk.Frame):
    def __init__(self, parent, app: POSApp):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="Cart & Checkout", font=("Helvetica", 14, "bold")).pack(pady=6)

        # Cart tree
        columns = ("product_id", "name", "qty", "price", "subtotal")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        for col, w in (("product_id",60),("name",200),("qty",60),("price",80),("subtotal",100)):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(padx=6, pady=4)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=6)
        ttk.Button(btns, text="Remove Selected", command=self.remove_selected).pack(side="left", padx=3)
        ttk.Button(btns, text="Clear Cart", command=self.clear_cart).pack(side="left", padx=3)
        ttk.Button(btns, text="Edit Qty", command=self.edit_qty).pack(side="left", padx=3)

        # Totals & customer
        frame2 = ttk.Frame(self)
        frame2.pack(fill="x", padx=6, pady=6)

        # Customer selector
        cust_frame = ttk.Frame(frame2)
        cust_frame.pack(fill="x", pady=3)
        ttk.Label(cust_frame, text="Customer:").pack(side="left")
        self.cust_var = tk.StringVar(value="Guest")
        self.cust_label = ttk.Label(cust_frame, textvariable=self.cust_var, width=38)
        self.cust_label.pack(side="left", padx=4)
        ttk.Button(cust_frame, text="Select/Add", command=self.select_customer).pack(side="left", padx=4)

        # Discount & payment
        tot_frame = ttk.Frame(frame2)
        tot_frame.pack(fill="x", pady=3)

        ttk.Label(tot_frame, text="Discount (%)").grid(row=0, column=0, sticky="e")
        self.disc_percent_var = tk.DoubleVar(value=0.0)
        ttk.Entry(tot_frame, textvariable=self.disc_percent_var, width=8).grid(row=0, column=1, padx=4)

        ttk.Label(tot_frame, text="Discount (Amt)").grid(row=0, column=2, sticky="e")
        self.disc_amt_var = tk.DoubleVar(value=0.0)
        ttk.Entry(tot_frame, textvariable=self.disc_amt_var, width=10).grid(row=0, column=3, padx=4)

        ttk.Label(tot_frame, text="Payment Method").grid(row=1, column=0, sticky="e", pady=6)
        self.pay_method_var = tk.StringVar(value="Cash")
        self.pay_method_cb = ttk.Combobox(tot_frame, textvariable=self.pay_method_var, values=["Cash","Card","PayWave","Online","Bank Transfer"], width=12, state="readonly")
        self.pay_method_cb.grid(row=1, column=1, padx=4)
        self.pay_method_cb.bind("<<ComboboxSelected>>", self.on_pay_method_change)

        # Second dropdown for card types (only shown when 'Card' is selected)
        ttk.Label(tot_frame, text="Card Type").grid(row=1, column=2, sticky="e")
        self.card_type_var = tk.StringVar(value="")
        self.card_type_cb = ttk.Combobox(tot_frame, textvariable=self.card_type_var, values=["Visa","MasterCard","Debit Card","Credit Card"], width=15, state="readonly")
        self.card_type_cb.grid(row=1, column=3, padx=4)
        # hide initially if not Card
        if self.pay_method_var.get() != "Card":
            self.card_type_cb.grid_remove()
            # hide label
            for w in tot_frame.grid_slaves(row=1, column=2):
                w.grid_remove()

        # Totals display
        display = ttk.Frame(self)
        display.pack(fill="x", padx=6, pady=6)
        self.sub_label = ttk.Label(display, text="Subtotal: $0.00")
        self.sub_label.pack(anchor="w")
        self.tax_label = ttk.Label(display, text=f"Tax ({TAX_RATE*100:.0f}%): $0.00")
        self.tax_label.pack(anchor="w")
        self.disc_label = ttk.Label(display, text="Discount: $0.00")
        self.disc_label.pack(anchor="w")
        self.total_label = ttk.Label(display, text="Grand Total: $0.00", font=("Helvetica", 12, "bold"))
        self.total_label.pack(anchor="w", pady=4)

        # Checkout
        chk_frame = ttk.Frame(self)
        chk_frame.pack(fill="x", padx=6, pady=6)
        ttk.Button(chk_frame, text="Recalculate", command=self.refresh_cart).pack(side="left")
        ttk.Button(chk_frame, text="Checkout", command=self.on_checkout).pack(side="right")

        # initial refresh
        self.refresh_cart()

    def on_pay_method_change(self, event=None):
        m = self.pay_method_var.get()
        # show card type combobox only when 'Card' chosen
        if m == "Card":
            # ensure label at (1,2) exists; we add label again if missing
            parent = self.card_type_cb.master
            # show label
            for w in parent.grid_slaves(row=1, column=2):
                w.grid()
            self.card_type_cb.grid()
        else:
            # hide card type combobox and its label
            self.card_type_cb.grid_remove()
            for w in self.card_type_cb.master.grid_slaves(row=1, column=2):
                w.grid_remove()
            self.card_type_var.set("")

    def refresh_cart(self):
        # refresh tree
        for i in self.tree.get_children():
            self.tree.delete(i)
        for item in self.app.cart:
            self.tree.insert("", "end", values=(item['product_id'], item['name'], item['qty'], f"{item['price']:.2f}", f"{item['subtotal']:.2f}"))
        # update customer label
        if self.app.selected_customer:
            self.cust_var.set(f"{self.app.selected_customer[1]} (ID:{self.app.selected_customer[0]})")
        else:
            self.cust_var.set("Guest")

        # update totals
        totals = self.app.compute_totals(self.disc_percent_var.get() or 0.0, self.disc_amt_var.get() or 0.0)
        self.sub_label.config(text=f"Subtotal: ${totals['subtotal']:.2f}")
        self.tax_label.config(text=f"Tax ({TAX_RATE*100:.0f}%): ${totals['tax']:.2f}")
        self.disc_label.config(text=f"Discount: ${totals['discount']:.2f}")
        self.total_label.config(text=f"Grand Total: ${totals['grand_total']:.2f}")

    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an item to remove.")
            return
        pid = int(self.tree.item(sel[0])['values'][0])
        self.app.remove_from_cart(pid)
        self.refresh_cart()

    def clear_cart(self):
        if not messagebox.askyesno("Confirm", "Clear cart?"):
            return
        self.app.clear_cart()
        self.refresh_cart()

    def edit_qty(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an item to edit.")
            return
        pid = int(self.tree.item(sel[0])['values'][0])
        current = next((i for i in self.app.cart if i['product_id']==pid), None)
        if not current:
            return
        new_qty = simpledialog.askinteger("Quantity", "Enter new quantity", initialvalue=current['qty'], minvalue=1)
        if new_qty is None:
            return
        # check stock
        row = db_query("SELECT stock FROM products WHERE id=?", (pid,), fetch=True)
        stock = row[0]['stock'] if row else None
        if stock is not None and new_qty > stock:
            messagebox.showwarning("Stock", f"Only {stock} available.")
            return
        current['qty'] = new_qty
        current['subtotal'] = current['price'] * new_qty
        self.refresh_cart()

    def select_customer(self):
        dialog = CustomerSelector(self)
        self.wait_window(dialog)
        if dialog.selected_customer:
            self.app.selected_customer = dialog.selected_customer
        self.refresh_cart()

    def on_checkout(self):
        discount_percent = float(self.disc_percent_var.get() or 0.0)
        discount_amount = float(self.disc_amt_var.get() or 0.0)
        payment_method = self.pay_method_var.get() or "Cash"
        payment_details = None
        if payment_method == "Card":
            payment_details = self.card_type_var.get() or "Card"
        # confirm message with payment details
        totals = self.app.compute_totals(discount_percent, discount_amount)
        pm_text = payment_method + (f" ({payment_details})" if payment_details else "")
        confirm = messagebox.askyesno("Confirm Payment", f"Charge ${totals['grand_total']:.2f} via {pm_text}?")
        if not confirm:
            return
        ok = self.app.checkout(payment_method, discount_percent, discount_amount, payment_details)
        if ok:
            messagebox.showinfo("Done", "Sale completed.")
            self.refresh_cart()


# ---------- Customer Selector ----------
class CustomerSelector(tk.Toplevel):
    def __init__(self, parent: CartCheckoutFrame):
        super().__init__(parent)
        self.title("Select / Add Customer")
        self.geometry("560x420")
        self.selected_customer = None

        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Search by name or phone:").pack(side="left")
        self.svar = tk.StringVar()
        ttk.Entry(top, textvariable=self.svar, width=30).pack(side="left", padx=6)
        ttk.Button(top, text="Search", command=self.search).pack(side="left", padx=4)
        ttk.Button(top, text="Show All", command=self.load_all).pack(side="left", padx=4)

        self.tree = ttk.Treeview(self, columns=("id","name","phone","email","points"), show="headings", height=14)
        for col,w in (("id",60),("name",180),("phone",120),("email",180),("points",80)):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=6)
        ttk.Button(btns, text="Select", command=self.select).pack(side="left", padx=4)
        ttk.Button(btns, text="Add New", command=self.add_new).pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right", padx=4)

        self.load_all()

    def load_all(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = db_query("SELECT id,name,phone,email,loyalty_points FROM customers ORDER BY id DESC", fetch=True) or []
        for r in rows:
            self.tree.insert("", "end", values=(r['id'], r['name'], r['phone'] or "", r['email'] or "", r['loyalty_points'] or 0))

    def search(self):
        t = self.svar.get().strip()
        if not t:
            self.load_all()
            return
        rows = db_query("SELECT id,name,phone,email,loyalty_points FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC", (f"%{t}%", f"%{t}%"), fetch=True) or []
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", "end", values=(r['id'], r['name'], r['phone'] or "", r['email'] or "", r['loyalty_points'] or 0))

    def select(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a customer.")
            return
        vals = self.tree.item(sel[0])['values']
        self.selected_customer = (vals[0], vals[1])
        self.destroy()

    def add_new(self):
        name = simpledialog.askstring("Name", "Customer name:")
        if not name:
            return
        phone = simpledialog.askstring("Phone", "Phone (optional):")
        email = simpledialog.askstring("Email", "Email (optional):")
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)", (name, phone, email))
        conn.commit()
        conn.close()
        messagebox.showinfo("Added", "Customer added.")
        self.load_all()


# ---------- Quick Product Manager (light weight) ----------
class ProductQuickManager(tk.Toplevel):
    def __init__(self, app: POSApp):
        super().__init__(app)
        self.title("Quick Product Manager")
        self.geometry("700x460")
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text="Add New Product").pack(anchor="w")
        form = ttk.Frame(self)
        form.pack(fill="x", padx=6)

        ttk.Label(form, text="Category").grid(row=0, column=0, sticky="e")
        self.cat_e = ttk.Entry(form, width=30); self.cat_e.grid(row=0, column=1, padx=4, pady=3)
        ttk.Label(form, text="Name").grid(row=1, column=0, sticky="e")
        self.name_e = ttk.Entry(form, width=40); self.name_e.grid(row=1, column=1, padx=4, pady=3)
        ttk.Label(form, text="Price").grid(row=2, column=0, sticky="e")
        self.price_e = ttk.Entry(form, width=20); self.price_e.grid(row=2, column=1, padx=4, pady=3)
        ttk.Label(form, text="Stock").grid(row=3, column=0, sticky="e")
        self.stock_e = ttk.Entry(form, width=20); self.stock_e.grid(row=3, column=1, padx=4, pady=3)
        ttk.Label(form, text="Barcode (optional)").grid(row=4, column=0, sticky="e")
        self.barcode_e = ttk.Entry(form, width=30); self.barcode_e.grid(row=4, column=1, padx=4, pady=3)

        ttk.Button(self, text="Add Product", command=self.add_product).pack(pady=6)
        ttk.Button(self, text="Close", command=self.destroy).pack(pady=6)

    def add_product(self):
        cat = self.cat_e.get().strip()
        name = self.name_e.get().strip()
        if not name:
            messagebox.showerror("Error", "Product name required.")
            return
        try:
            price = float(self.price_e.get().strip() or 0.0)
        except:
            messagebox.showerror("Error", "Invalid price.")
            return
        try:
            stock = int(self.stock_e.get().strip() or 0)
        except:
            messagebox.showerror("Error", "Invalid stock.")
            return
        barcode = self.barcode_e.get().strip() or None
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO products (category, name, price, stock, barcode) VALUES (?, ?, ?, ?, ?)", (cat, name, price, stock, barcode))
        conn.commit()
        conn.close()
        messagebox.showinfo("Added", "Product added.")
        # refresh product lists in main window (simple reload)
        self.app.product_search_frame.load_all()
        self.destroy()


# ---------- Run ----------
if __name__ == "__main__":
    init_db()
    app = POSApp()
    app.mainloop()
