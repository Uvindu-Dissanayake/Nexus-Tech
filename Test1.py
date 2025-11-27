import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3, csv, random
from datetime import datetime
import matplotlib.pyplot as plt

# ---------------- CONFIG ----------------
DB_FILE = 'shop.db'
CATEGORIES = [
    "Laptops", "Phones", "Tablets", "Monitors", "Keyboards",
    "Mice", "Headphones", "Smartwatches", "Printers", "Components"
]

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Users table
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        card_number TEXT,
        loyalty_points INTEGER DEFAULT 0
    )''')

    # Products: added stock column
    cur.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        name TEXT,
        price REAL,
        stock INTEGER DEFAULT 10
    )''')

    # Orders table
    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        total REAL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Order products (line items)
    cur.execute('''CREATE TABLE IF NOT EXISTS order_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )''')

    conn.commit()

    # Seed products on first run
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        for cat in CATEGORIES:
            for i in range(1, 11):
                name = f"{cat[:-1]} Model {i}"
                price = round(random.uniform(99, 2499), 2)
                stock = random.randint(5, 50)
                cur.execute("INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
                            (cat, name, price, stock))
        conn.commit()
        print("✅ Products populated")

    # Create default staff if missing
    cur.execute("SELECT id FROM users WHERE username=?", ('staff1',))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ('staff1', 'password123', 'staff'))
        conn.commit()
        print("👨‍💼 Default staff created (staff1/password123)")

    conn.close()

# ---------------- APP CONTROLLER ----------------
class ShopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nexus Tech Shop")
        self.geometry("1000x700")
        self.current_user = None
        self.frames = {}
        # Keep a persistent connection for the app
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        for F in (StartPage, CustomerLoginPage, StaffLoginPage, AdminLoginPage,
                  RegisterPage, CustomerAccountPage, ShoppingPage,
                  StaffPage, AdminReportsPage):
            page_name = F.__name__
            frame = F(container, self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, 'refresh'):
            frame.refresh(self)

    def query(self, sql, params=(), fetch=False):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        if fetch:
            rows = cur.fetchall()
            return rows
        self.conn.commit()
        return None

# ---------------- START PAGE ----------------
class StartPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Welcome to Nexus Tech Shop", font=('Helvetica',18,'bold')).pack(pady=30)
        ttk.Button(self, text="Customer Login", command=lambda: controller.show_frame("CustomerLoginPage")).pack(pady=6)
        ttk.Button(self, text="Customer Registration", command=lambda: controller.show_frame("RegisterPage")).pack(pady=6)
        ttk.Button(self, text="Staff Login", command=lambda: controller.show_frame("StaffLoginPage")).pack(pady=6)
        ttk.Button(self, text="Admin Login", command=lambda: controller.show_frame("AdminLoginPage")).pack(pady=6)

# ---------------- CUSTOMER REGISTER ----------------
class RegisterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Customer Registration", font=('Helvetica',16,'bold')).pack(pady=10)

        frm = ttk.Frame(self)
        frm.pack(pady=6)

        ttk.Label(frm, text="Username:").grid(row=0, column=0, sticky='e')
        self.username = ttk.Entry(frm); self.username.grid(row=0, column=1, padx=6, pady=2)
        ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky='e')
        self.password = ttk.Entry(frm, show='*'); self.password.grid(row=1, column=1, padx=6, pady=2)
        ttk.Label(frm, text="Card Number:").grid(row=2, column=0, sticky='e')
        self.card = ttk.Entry(frm); self.card.grid(row=2, column=1, padx=6, pady=2)

        ttk.Button(self, text="Register", command=lambda: self.register(controller)).pack(pady=8)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def register(self, controller):
        u = self.username.get().strip()
        p = self.password.get().strip()
        c = self.card.get().strip()
        if not (u and p and c):
            messagebox.showwarning("Missing", "Please fill all fields.")
            return
        try:
            controller.query("INSERT INTO users (username, password, role, card_number) VALUES (?, ?, 'customer', ?)",
                             (u, p, c))
            messagebox.showinfo("OK", "Registered. You can now login as customer.")
            controller.show_frame("CustomerLoginPage")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists.")

# ---------------- CUSTOMER LOGIN ----------------
class CustomerLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Customer Login", font=('Helvetica',16,'bold')).pack(pady=10)

        frm = ttk.Frame(self); frm.pack(pady=6)
        ttk.Label(frm, text="Username:").grid(row=0,column=0,sticky='e')
        self.username = ttk.Entry(frm); self.username.grid(row=0,column=1,padx=6)
        ttk.Label(frm, text="Password:").grid(row=1,column=0,sticky='e')
        self.password = ttk.Entry(frm, show='*'); self.password.grid(row=1,column=1,padx=6)

        ttk.Button(self, text="Login", command=lambda: self.login(controller)).pack(pady=8)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def login(self, controller):
        u = self.username.get().strip(); p = self.password.get().strip()
        rows = controller.query("SELECT * FROM users WHERE username=? AND password=? AND role='customer'", (u,p), fetch=True)
        if rows:
            controller.current_user = dict(rows[0])
            controller.show_frame("CustomerAccountPage")
        else:
            messagebox.showerror("Login Failed", "Incorrect username or password.")

# ---------------- STAFF LOGIN ----------------
class StaffLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Staff Login", font=('Helvetica',16,'bold')).pack(pady=10)
        frm = ttk.Frame(self); frm.pack(pady=6)
        ttk.Label(frm, text="Username:").grid(row=0,column=0,sticky='e')
        self.username = ttk.Entry(frm); self.username.grid(row=0,column=1,padx=6)
        ttk.Label(frm, text="Password:").grid(row=1,column=0,sticky='e')
        self.password = ttk.Entry(frm, show='*'); self.password.grid(row=1,column=1,padx=6)
        ttk.Button(self, text="Login", command=lambda: self.login(controller)).pack(pady=8)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def login(self, controller):
        u = self.username.get().strip(); p = self.password.get().strip()
        rows = controller.query("SELECT * FROM users WHERE username=? AND password=? AND role='staff'", (u,p), fetch=True)
        if rows:
            controller.current_user = dict(rows[0])
            controller.show_frame("StaffPage")
        else:
            messagebox.showerror("Login Failed", "Incorrect staff credentials.")

# ---------------- ADMIN LOGIN ----------------
class AdminLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Admin Login", font=('Helvetica',16,'bold')).pack(pady=10)
        frm = ttk.Frame(self); frm.pack(pady=6)
        ttk.Label(frm, text="Username:").grid(row=0,column=0,sticky='e')
        self.username = ttk.Entry(frm); self.username.grid(row=0,column=1,padx=6)
        ttk.Label(frm, text="Password:").grid(row=1,column=0,sticky='e')
        self.password = ttk.Entry(frm, show='*'); self.password.grid(row=1,column=1,padx=6)
        ttk.Button(self, text="Login", command=lambda: self.login(controller)).pack(pady=8)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def login(self, controller):
        # Admin credential is fixed as requested
        if self.username.get() == "Admin" and self.password.get() == "admin123":
            controller.show_frame("AdminReportsPage")
        else:
            messagebox.showerror("Login Failed", "Incorrect admin credentials.")

# ---------------- CUSTOMER ACCOUNT ----------------
class CustomerAccountPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Customer Account", font=('Helvetica',16,'bold')).pack(pady=10)
        self.info = ttk.Label(self, text="", justify='left')
        self.info.pack(pady=6)
        ttk.Button(self, text="Go Shopping", command=lambda: controller.show_frame("ShoppingPage")).pack(pady=4)
        ttk.Button(self, text="Logout", command=lambda: self.logout(controller)).pack(pady=4)

    def refresh(self, controller):
        u = controller.current_user
        if not u:
            self.info.config(text="Not logged in.")
            return
        # reload latest loyalty points and card
        row = controller.query("SELECT loyalty_points, card_number FROM users WHERE id=?", (u['id'],), fetch=True)
        if row:
            lp = row[0]['loyalty_points']; card = row[0]['card_number']
            controller.current_user['loyalty_points'] = lp
            controller.current_user['card_number'] = card
            self.info.config(text=f"Username: {u['username']}\nLoyalty Points: {lp}\nCard: {card or 'No card'}")

    def logout(self, controller):
        controller.current_user = None
        controller.show_frame("StartPage")

# ---------------- SHOPPING PAGE ----------------
class ShoppingPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Shopping', font=('Helvetica',16)).pack(pady=8)

        top = ttk.Frame(self); top.pack(fill='x')
        ttk.Button(top, text='Back', command=lambda: controller.show_frame('CustomerAccountPage')).pack(side='left', padx=6)
        ttk.Button(top, text='View Cart', command=self.view_cart).pack(side='right', padx=6)

        content = ttk.Frame(self); content.pack(fill='both', expand=True, padx=8, pady=8)

        left = ttk.Frame(content); left.pack(side='left', fill='y')
        ttk.Label(left, text='Categories').pack()
        self.cat_list = tk.Listbox(left, height=20); self.cat_list.pack()
        for c in CATEGORIES: self.cat_list.insert('end', c)
        self.cat_list.bind('<<ListboxSelect>>', self.show_products)

        right = ttk.Frame(content); right.pack(side='left', fill='both', expand=True)
        self.tree = ttk.Treeview(right, columns=('id','name','price','stock'), show='headings')
        for col in ('id','name','price','stock'):
            self.tree.heading(col, text=col.title()); self.tree.column(col, anchor='center')
        self.tree.pack(fill='both', expand=True)

        bottom = ttk.Frame(self); bottom.pack(fill='x', pady=6)
        ttk.Button(bottom, text='Add Selected to Cart', command=self.add_to_cart).pack(side='left', padx=6)
        ttk.Button(bottom, text='Checkout', command=self.checkout).pack(side='left', padx=6)
        self.total_label = ttk.Label(bottom, text='Total: $0.00'); self.total_label.pack(side='right', padx=6)

        # cart as list of (product_id, qty)
        self.cart = []

    def refresh(self, controller=None):
        self.show_products()
        self.update_total()

    def show_products(self, event=None):
        sel = self.cat_list.curselection()
        if sel:
            cat = self.cat_list.get(sel[0])
            rows = self.controller.query('SELECT id,name,price,stock FROM products WHERE category=?', (cat,), fetch=True)
        else:
            rows = self.controller.query('SELECT id,name,price,stock FROM products', fetch=True)
        rows = rows or []
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in rows:
            self.tree.insert('', 'end', values=(r['id'], r['name'], f"{r['price']:.2f}", r['stock']))

    def add_to_cart(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Select','Select a product first')
            return
        vals = self.tree.item(sel[0])['values']
        pid = int(vals[0])
        stock = int(vals[3]) if vals[3] is not None else None
        qty = simpledialog.askinteger('Quantity', 'Quantity to add', minvalue=1, initialvalue=1)
        if not qty: return
        if stock is not None and qty > stock:
            messagebox.showwarning('Stock','Requested quantity exceeds stock')
            return
        # merge into cart
        for i,(epid,eq) in enumerate(self.cart):
            if epid == pid:
                self.cart[i] = (epid, eq+qty)
                break
        else:
            self.cart.append((pid, qty))
        self.update_total()
        messagebox.showinfo('Cart','Added to cart')

    def update_total(self):
        total = 0.0
        for pid, qty in self.cart:
            row = self.controller.query('SELECT price FROM products WHERE id=?', (pid,), fetch=True)
            if not row: continue
            total += row[0]['price'] * qty
        self.total_label.config(text=f'Total: ${total:.2f}')

    def view_cart(self):
        if not self.cart:
            messagebox.showinfo('Cart','Cart is empty'); return
        top = tk.Toplevel(self); top.title('Cart Details')
        tree = ttk.Treeview(top, columns=('name','qty','price','subtotal'), show='headings')
        for c in ('name','qty','price','subtotal'): tree.heading(c, text=c.title())
        tree.pack(fill='both', expand=True)
        total = 0.0
        for pid, qty in self.cart:
            row = self.controller.query('SELECT name,price FROM products WHERE id=?', (pid,), fetch=True)
            if not row: continue
            name = row[0]['name']; price = row[0]['price']; sub = price * qty
            total += sub
            tree.insert('', 'end', values=(name, qty, f"{price:.2f}", f"{sub:.2f}"))
        ttk.Label(top, text=f"Total: ${total:.2f}").pack(pady=6)

    def checkout(self):
        if not self.cart:
            messagebox.showinfo('Empty','Cart is empty'); return
        # compute and check stock
        total = 0.0
        for pid, qty in self.cart:
            row = self.controller.query('SELECT price,stock FROM products WHERE id=?', (pid,), fetch=True)
            if not row:
                messagebox.showerror('Error', f'Product {pid} not found'); return
            price = row[0]['price']; stock = row[0]['stock']
            if stock is not None and qty > stock:
                messagebox.showwarning('Stock', f'Not enough stock for {pid}.'); return
            total += price * qty

        u = self.controller.current_user
        if not u or u.get('role') != 'customer':
            messagebox.showinfo('Guest','You must be logged in as a customer to checkout'); return
        card = u.get('card_number')
        if not card:
            messagebox.showwarning('No Card','Add a card in account first'); return
        confirm = messagebox.askyesno('Payment', f'Charge ${total:.2f} to card ending {str(card)[-4:]}?')
        if not confirm: return

        # perform DB transaction
        cur = self.controller.conn.cursor()
        try:
            cur.execute('INSERT INTO orders (user_id, total, timestamp) VALUES (?, ?, ?)',
                        (u['id'], total, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            order_id = cur.lastrowid
            for pid, qty in self.cart:
                cur.execute('INSERT INTO order_products (order_id, product_id, quantity) VALUES (?, ?, ?)',
                            (order_id, pid, qty))
                cur.execute('UPDATE products SET stock = stock - ? WHERE id=?', (qty, pid))
            # loyalty points
            points = int(total // 10)
            cur.execute('UPDATE users SET loyalty_points = loyalty_points + ? WHERE id=?', (points, u['id']))
            self.controller.conn.commit()
        except Exception as e:
            self.controller.conn.rollback()
            messagebox.showerror('Error', f'Order failed: {e}')
            return

        messagebox.showinfo('Success', f'Payment processed (simulated). Earned {points} loyalty points.')
        self.cart.clear()
        self.update_total()
        # refresh customer account and product list
        self.controller.show_frame('CustomerAccountPage')
        self.show_products()

# ---------------- STAFF PAGE ----------------
class StaffPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Staff Management Dashboard", font=("Helvetica", 16, "bold")).pack(pady=10)

        # Top Buttons
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(top_frame, text="Back", command=lambda: controller.show_frame("StartPage")).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Logout", command=lambda: controller.logout()).pack(side="left", padx=5)

        # Product Management Section
        ttk.Label(self, text="Product Management", font=("Helvetica", 13, "bold")).pack(pady=10)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Add Product", command=lambda: self.add_product(controller)).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Update Product", command=lambda: self.update_product(controller)).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete Product", command=lambda: self.delete_product(controller)).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="Seed Sample Products", command=lambda: self.seed_sample_products(controller)).grid(row=0, column=3, padx=5)

        # Product Table
        columns = ("id", "category", "name", "price")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=150)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh_products(controller)

    def refresh_products(self, controller):
        for row in self.tree.get_children():
            self.tree.delete(row)
        products = controller.query("SELECT * FROM products", fetch=True)
        for p in products:
            self.tree.insert("", "end", values=p)

    # --- ADD PRODUCT ---
    def add_product(self, controller):
        popup = tk.Toplevel(self)
        popup.title("Add Product")
        popup.geometry("300x250")
        ttk.Label(popup, text="Category").pack(pady=5)
        category_entry = ttk.Entry(popup)
        category_entry.pack(pady=5)
        ttk.Label(popup, text="Product Name").pack(pady=5)
        name_entry = ttk.Entry(popup)
        name_entry.pack(pady=5)
        ttk.Label(popup, text="Price ($)").pack(pady=5)
        price_entry = ttk.Entry(popup)
        price_entry.pack(pady=5)

        def save():
            category = category_entry.get()
            name = name_entry.get()
            try:
                price = float(price_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Price must be a number.")
                return
            if not category or not name:
                messagebox.showerror("Error", "All fields required.")
                return
            controller.query("INSERT INTO products (category, name, price) VALUES (?, ?, ?)", (category, name, price))
            controller.conn.commit()
            messagebox.showinfo("Success", "Product added successfully.")
            popup.destroy()
            self.refresh_products(controller)

        ttk.Button(popup, text="Save", command=save).pack(pady=10)

    # --- UPDATE PRODUCT ---
    def update_product(self, controller):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a product to update.")
            return
        item = self.tree.item(selected[0])["values"]
        product_id, old_cat, old_name, old_price = item

        popup = tk.Toplevel(self)
        popup.title("Update Product")
        popup.geometry("300x250")
        ttk.Label(popup, text="Category").pack(pady=5)
        category_entry = ttk.Entry(popup)
        category_entry.insert(0, old_cat)
        category_entry.pack(pady=5)
        ttk.Label(popup, text="Product Name").pack(pady=5)
        name_entry = ttk.Entry(popup)
        name_entry.insert(0, old_name)
        name_entry.pack(pady=5)
        ttk.Label(popup, text="Price ($)").pack(pady=5)
        price_entry = ttk.Entry(popup)
        price_entry.insert(0, old_price)
        price_entry.pack(pady=5)

        def save_update():
            cat = category_entry.get()
            name = name_entry.get()
            try:
                price = float(price_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Price must be a number.")
                return
            if not cat or not name:
                messagebox.showerror("Error", "All fields required.")
                return
            controller.query("UPDATE products SET category=?, name=?, price=? WHERE id=?", (cat, name, price, product_id))
            controller.conn.commit()
            messagebox.showinfo("Success", "Product updated successfully.")
            popup.destroy()
            self.refresh_products(controller)

        ttk.Button(popup, text="Save Changes", command=save_update).pack(pady=10)

    # --- DELETE PRODUCT ---
    def delete_product(self, controller):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a product to delete.")
            return
        item = self.tree.item(selected[0])["values"]
        product_id = item[0]
        confirm = messagebox.askyesno("Confirm Delete", f"Delete product '{item[2]}'?")
        if confirm:
            controller.query("DELETE FROM products WHERE id=?", (product_id,))
            controller.conn.commit()
            messagebox.showinfo("Deleted", "Product deleted successfully.")
            self.refresh_products(controller)

    # --- SEED DEFAULT PRODUCTS ---
    def seed_sample_products(self, controller):
        confirm = messagebox.askyesno(
            "Confirm Seed",
            "This will delete all existing products and re-add the 10 default categories × 10 products.\n\nDo you want to continue?"
        )
        if not confirm:
            return

        controller.query("DELETE FROM products")
        controller.conn.commit()

        categories = [
            "Laptops", "Phones", "Tablets", "Monitors", "Keyboards",
            "Mice", "Headphones", "Smartwatches", "Printers", "Components"
        ]
        for cat in categories:
            for i in range(1, 11):
                name = f"{cat[:-1]} Model {i}"
                price = round(random.uniform(99, 2499), 2)
                controller.query("INSERT INTO products (category, name, price) VALUES (?, ?, ?)", (cat, name, price))
        controller.conn.commit()
        messagebox.showinfo("Database Seeded", "Default products have been repopulated successfully!")
        self.refresh_products(controller)

# ---------------- ADMIN REPORTS ----------------
class AdminReportsPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Admin Reports Dashboard", font=('Helvetica',16,'bold')).pack(pady=10)

        top = ttk.Frame(self); top.pack(fill='x', padx=10, pady=6)
        ttk.Button(top, text="Back", command=lambda: controller.show_frame("StartPage")).pack(side='left')
        ttk.Button(top, text="Refresh", command=lambda: self.refresh(controller)).pack(side='left', padx=6)
        self.filter_var = tk.StringVar(value="All Time")
        ttk.OptionMenu(top, self.filter_var, "All Time", "All Time", "Today", "This Week", "This Month").pack(side='left', padx=6)
        ttk.Button(top, text="Export CSV", command=lambda: self.export_csv(controller)).pack(side='right')

        self.tree = ttk.Treeview(self, columns=('customer','total','timestamp'), show='headings')
        for c in ('customer','total','timestamp'):
            self.tree.heading(c, text=c.title()); self.tree.column(c, anchor='center')
        self.tree.pack(fill='both', expand=True, padx=10, pady=6)

    def refresh(self, controller):
        f = self.filter_var.get()
        clause = ""
        if f == 'Today': clause = "WHERE date(o.timestamp)=date('now')"
        elif f == 'This Week': clause = "WHERE date(o.timestamp) >= date('now', '-7 day')"
        elif f == 'This Month': clause = "WHERE strftime('%Y-%m', o.timestamp) = strftime('%Y-%m','now')"

        rows = controller.query(f"""
            SELECT u.username AS customer, o.total AS total, o.timestamp AS timestamp
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            {clause}
            ORDER BY o.timestamp DESC
        """, fetch=True) or []

        for i in self.tree.get_children(): self.tree.delete(i)
        for r in rows:
            self.tree.insert('', 'end', values=(r['customer'], f"{r['total']:.2f}", r['timestamp']))
        self._data = rows

    def export_csv(self, controller):
        if not hasattr(self, '_data') or not self._data:
            messagebox.showwarning("No Data", "Refresh first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not path: return
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Customer','Total','Timestamp'])
            for r in self._data:
                w.writerow([r['customer'], r['total'], r['timestamp']])
        messagebox.showinfo("Exported", f"Saved to {path}")

    def show_sales_chart(self):
        if not hasattr(self, '_data') or not self._data:
            messagebox.showwarning("No Data", "Refresh first.")
            return
        sales = {}
        for r in self._data:
            day = r['timestamp'].split()[0]
            sales[day] = sales.get(day, 0) + float(r['total'])
        dates = sorted(sales.keys()); totals = [sales[d] for d in dates]
        plt.figure(figsize=(8,4)); plt.bar(dates, totals); plt.xticks(rotation=45); plt.title("Sales Over Time"); plt.tight_layout(); plt.show()

    def show_analytics(self):
        # Top 5 products by quantity sold
        products = self.controller.query("""
            SELECT p.name AS name, SUM(op.quantity) AS sold
            FROM order_products op
            JOIN products p ON p.id = op.product_id
            GROUP BY p.id
            ORDER BY sold DESC
            LIMIT 5
        """, fetch=True) or []

        # Top 5 customers by orders
        customers = self.controller.query("""
            SELECT u.username AS username, COUNT(o.id) AS orders_count
            FROM orders o
            JOIN users u ON u.id = o.user_id
            GROUP BY u.id
            ORDER BY orders_count DESC
            LIMIT 5
        """, fetch=True) or []

        msg = "Top 5 Products (by units sold):\n"
        msg += "\n".join(f"{r['name']}: {int(r['sold'])}" for r in products) if products else "No data\n"
        msg += "\n\nTop 5 Customers (by orders):\n"
        msg += "\n".join(f"{r['username']}: {r['orders_count']}" for r in customers) if customers else "No data\n"
        messagebox.showinfo("Analytics", msg)

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app = ShopApp()
    app.mainloop()
