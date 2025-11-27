import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3, csv, random
from datetime import datetime
import matplotlib.pyplot as plt

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect('shop.db')
cur = conn.cursor()

# --- Create Tables ---
cur.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT,
    card_number TEXT,
    loyalty_points INTEGER DEFAULT 0
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    name TEXT,
    price REAL
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    total REAL,
    timestamp TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')

conn.commit()

# --- AUTO-POPULATE PRODUCTS ON FIRST RUN ---
categories = [
    "Laptops", "Phones", "Tablets", "Monitors", "Keyboards",
    "Mice", "Headphones", "Smartwatches", "Printers", "Components"
]

cur.execute("SELECT COUNT(*) FROM products")
count = cur.fetchone()[0]

if count == 0:
    print("🛒 Populating database with default products...")
    for cat in categories:
        for i in range(1, 11):
            name = f"{cat[:-1]} Model {i}"
            price = round(random.uniform(99, 2499), 2)
            cur.execute("INSERT INTO products (category, name, price) VALUES (?, ?, ?)", (cat, name, price))
    conn.commit()
    print("✅ Products added successfully!")

# --- AUTO-CREATE DEFAULT STAFF ACCOUNT ---
default_staff = ('staff1', 'password123', 'staff')
cur.execute("SELECT * FROM users WHERE username=?", (default_staff[0],))
if not cur.fetchone():
    cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", default_staff)
    conn.commit()
    print("👨‍💼 Default staff account created: username='staff1', password='password123'")


# ---------------- APP CONTROLLER ----------------
class ShopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nexus Tech Shop")
        self.geometry("900x600")
        self.current_user = None
        self.frames = {}

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
        conn = sqlite3.connect('shop.db')
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        if fetch:
            return cur.fetchall()

# ---------------- START PAGE ----------------
class StartPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Welcome to Nexus Tech Shop", font=('Helvetica',18,'bold')).pack(pady=30)
        ttk.Button(self, text="Customer Login", command=lambda: controller.show_frame("CustomerLoginPage")).pack(pady=5)
        ttk.Button(self, text="Staff Login", command=lambda: controller.show_frame("StaffLoginPage")).pack(pady=5)
        ttk.Button(self, text="Admin Login", command=lambda: controller.show_frame("AdminLoginPage")).pack(pady=5)
        ttk.Button(self, text="Register as Customer", command=lambda: controller.show_frame("RegisterPage")).pack(pady=5)

# ---------------- CUSTOMER LOGIN ----------------
class CustomerLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Customer Login", font=('Helvetica',16,'bold')).pack(pady=10)

        self.user = tk.StringVar()
        self.pw = tk.StringVar()

        ttk.Label(self, text="Username").pack()
        ttk.Entry(self, textvariable=self.user).pack()
        ttk.Label(self, text="Password").pack()
        ttk.Entry(self, textvariable=self.pw, show="*").pack()

        ttk.Button(self, text="Login", command=lambda: self.login(controller)).pack(pady=5)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def login(self, controller):
        user = controller.query("SELECT * FROM users WHERE username=? AND password=? AND role='customer'",
                                (self.user.get(), self.pw.get()), fetch=True)
        if user:
            controller.current_user = user[0]
            controller.show_frame("CustomerAccountPage")
        else:
            messagebox.showerror("Login Failed", "Incorrect username or password.")

# ---------------- STAFF LOGIN ----------------
class StaffLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Staff Login", font=('Helvetica',16,'bold')).pack(pady=10)
        self.user = tk.StringVar()
        self.pw = tk.StringVar()
        ttk.Label(self, text="Username").pack()
        ttk.Entry(self, textvariable=self.user).pack()
        ttk.Label(self, text="Password").pack()
        ttk.Entry(self, textvariable=self.pw, show="*").pack()
        ttk.Button(self, text="Login", command=lambda: self.login(controller)).pack(pady=5)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def login(self, controller):
        user = controller.query("SELECT * FROM users WHERE username=? AND password=? AND role='staff'",
                                (self.user.get(), self.pw.get()), fetch=True)
        if user:
            controller.current_user = user[0]
            controller.show_frame("StaffPage")
        else:
            messagebox.showerror("Login Failed", "Incorrect staff credentials.")

# ---------------- ADMIN LOGIN ----------------
class AdminLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Admin Login", font=('Helvetica',16,'bold')).pack(pady=10)
        self.user = tk.StringVar()
        self.pw = tk.StringVar()
        ttk.Label(self, text="Username").pack()
        ttk.Entry(self, textvariable=self.user).pack()
        ttk.Label(self, text="Password").pack()
        ttk.Entry(self, textvariable=self.pw, show="*").pack()
        ttk.Button(self, text="Login", command=lambda: self.login(controller)).pack(pady=5)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def login(self, controller):
        if self.user.get() == "Admin" and self.pw.get() == "admin123":
            controller.show_frame("AdminReportsPage")
        else:
            messagebox.showerror("Login Failed", "Incorrect admin credentials.")

# ---------------- REGISTER PAGE ----------------
class RegisterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Customer Registration", font=('Helvetica',16,'bold')).pack(pady=10)
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.card = tk.StringVar()

        ttk.Label(self, text="Username").pack()
        ttk.Entry(self, textvariable=self.username).pack()
        ttk.Label(self, text="Password").pack()
        ttk.Entry(self, textvariable=self.password, show="*").pack()
        ttk.Label(self, text="Card Number").pack()
        ttk.Entry(self, textvariable=self.card).pack()

        ttk.Button(self, text="Register", command=lambda: self.register(controller)).pack(pady=5)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def register(self, controller):
        try:
            controller.query("INSERT INTO users (username, password, role, card_number) VALUES (?, ?, 'customer', ?)",
                             (self.username.get(), self.password.get(), self.card.get()))
            messagebox.showinfo("Success", "Registration successful.")
            controller.show_frame("CustomerLoginPage")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists.")

# ---------------- CUSTOMER ACCOUNT ----------------
class CustomerAccountPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Customer Account", font=('Helvetica',16,'bold')).pack(pady=10)
        self.info = ttk.Label(self, text="")
        self.info.pack(pady=5)
        ttk.Button(self, text="Go Shopping", command=lambda: controller.show_frame("ShoppingPage")).pack(pady=5)
        ttk.Button(self, text="Logout", command=lambda: controller.show_frame("StartPage")).pack()

    def refresh(self, controller):
        user = controller.current_user
        if user:
            self.info.config(text=f"Welcome, {user[1]}!\nLoyalty Points: {user[5]}")

# ---------------- SHOPPING PAGE ----------------
class ShoppingPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Shopping Page', font=('Helvetica', 16)).pack(pady=8)
        top = ttk.Frame(self)
        top.pack(fill='x')
        ttk.Button(top, text='Back', command=lambda: controller.show_frame('StartPage')).pack(side='left')
        ttk.Button(top, text='View Cart', command=self.view_cart).pack(side='right')

        mid = ttk.Frame(self)
        mid.pack(fill='both', expand=True)

        self.cat_list = tk.Listbox(mid, height=20)
        self.cat_list.pack(side='left', fill='y')
        for c in CATEGORIES:
            self.cat_list.insert('end', c)
        self.cat_list.bind('<<ListboxSelect>>', self.show_products)

        self.tree = ttk.Treeview(mid, columns=('id', 'name', 'price', 'stock'), show='headings')
        for col in ('id', 'name', 'price', 'stock'):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, anchor='center')
        self.tree.pack(side='left', fill='both', expand=True)

        bottom = ttk.Frame(self)
        bottom.pack(fill='x', pady=6)
        ttk.Button(bottom, text='Add to Cart', command=self.add_to_cart).pack(side='left', padx=4)
        ttk.Button(bottom, text='Checkout', command=self.checkout).pack(side='left', padx=4)
        self.total_label = ttk.Label(bottom, text='Total: $0.00')
        self.total_label.pack(side='right')

    # refresh may be called with controller param from show_frame
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
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert('', 'end', values=r)

    def add_to_cart(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select an item')
            return
        vals = self.tree.item(sel[0])['values']
        pid, name, price, stock = vals[0], vals[1], vals[2], vals[3]
        qty = simpledialog.askinteger('Quantity', 'Enter quantity', minvalue=1, initialvalue=1)
        if qty:
            if stock is not None and qty > stock:
                messagebox.showwarning('Stock', f'Only {stock} items available.')
                return
            # try to merge with existing cart entry
            for idx, (existing_pid, existing_qty) in enumerate(self.controller.cart):
                if existing_pid == pid:
                    self.controller.cart[idx] = (existing_pid, existing_qty + qty)
                    break
            else:
                self.controller.cart.append((pid, qty))
            self.update_total()

    def update_total(self):
        total = 0.0
        for pid, qty in self.controller.cart:
            row = self.controller.query('SELECT price FROM products WHERE id=?', (pid,), fetch=True)
            if not row:
                continue
            price = row[0][0]
            total += price * qty
        self.total_label.config(text=f'Total: ${total:.2f}')

    def view_cart(self):
        if not self.controller.cart:
            messagebox.showinfo('Cart', 'Cart is empty')
            return
        top = tk.Toplevel(self)
        top.title('Cart Details')
        tree = ttk.Treeview(top, columns=('name', 'qty', 'price', 'subtotal'), show='headings')
        for c in ('name', 'qty', 'price', 'subtotal'):
            tree.heading(c, text=c.title())
            tree.column(c, anchor='center')
        tree.pack(fill='both', expand=True)
        total = 0
        for pid, qty in self.controller.cart:
            row = self.controller.query('SELECT name,price FROM products WHERE id=?', (pid,), fetch=True)
            if not row:
                continue
            n, p = row[0]
            sub = p * qty
            total += sub
            tree.insert('', 'end', values=(n, qty, f'{p:.2f}', f'{sub:.2f}'))
        ttk.Label(top, text=f'Total: ${total:.2f}').pack(pady=6)

    def checkout(self):
        if not self.controller.cart:
            messagebox.showinfo('Empty', 'Cart is empty')
            return

        # compute total and check stock availability
        total = 0.0
        for pid, qty in self.controller.cart:
            row = self.controller.query('SELECT price, stock FROM products WHERE id=?', (pid,), fetch=True)
            if not row:
                messagebox.showerror('Error', f'Product id {pid} not found.')
                return
            price, stock = row[0]
            if stock is not None and qty > stock:
                messagebox.showwarning('Stock', f'Not enough stock for product id {pid}. Available: {stock}')
                return
            total += price * qty

        u = self.controller.current_user
        if not u or (u and u[3] != 'customer'):
            messagebox.showinfo('Guest', 'You must be logged in as a customer to pay with card.')
            return

        card_number = u[4]
        if not card_number:
            messagebox.showwarning('No Card', 'Add a card in your account first.')
            return

        confirm = messagebox.askyesno('Payment', f'Charge ${total:.2f} to card ending {str(card_number)[-4:]}?')
        if not confirm:
            return

        # perform DB insert for order and order_products and decrement stock
        conn = sqlite3.connect(DB_FILE)
        conn.execute("PRAGMA foreign_keys = ON;")
        c = conn.cursor()
        try:
            c.execute('INSERT INTO orders (user_id, total) VALUES (?, ?)', (u[0], total))
            order_id = c.lastrowid
            for pid, qty in self.controller.cart:
                c.execute('INSERT INTO order_products (order_id, product_id, quantity) VALUES (?, ?, ?)', (order_id, pid, qty))
                # decrement stock
                c.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (qty, pid))
            # award loyalty points (1 point per $10)
            points = int(total // 10)
            c.execute('UPDATE users SET loyalty_points = loyalty_points + ? WHERE id=?', (points, u[0]))
            conn.commit()
        except Exception as e:
            conn.rollback()
            messagebox.showerror('Error', f'Failed to place order: {e}')
            conn.close()
            return
        conn.close()

        messagebox.showinfo('Payment', 'Payment successful (simulated).')
        self.controller.cart.clear()
        self.update_total()
        messagebox.showinfo('Done', f'Order completed, earned {points} loyalty points.')


# ---------------- STAFF PAGE ----------------
class StaffPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Staff Management", font=('Helvetica',16,'bold')).pack(pady=10)
        ttk.Button(self, text="Manage Customers", command=self.manage_customers).pack(pady=5)
        ttk.Button(self, text="Manage Products", command=self.manage_products).pack(pady=5)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack(pady=5)
        ttk.Button(self, text="Seed Sample Products", command=lambda: self.seed_sample_products(controller)).pack(pady=10)


    def manage_customers(self):
        win = tk.Toplevel(self)
        win.title("Customer Management")
        tree = ttk.Treeview(win, columns=('id','username','card'), show='headings')
        for c in ('id','username','card'):
            tree.heading(c, text=c.capitalize())
        tree.pack(fill='both', expand=True)
        customers = conn.execute("SELECT id,username,card_number FROM users WHERE role='customer'").fetchall()
        for c in customers:
            tree.insert('', 'end', values=c)
        ttk.Button(win, text="Delete Selected", command=lambda: self.del_customer(tree)).pack(pady=5)

    def del_customer(self, tree):
        sel = tree.selection()
        if not sel: return
        cid = tree.item(sel[0])['values'][0]
        conn.execute("DELETE FROM users WHERE id=?", (cid,))
        conn.commit()
        tree.delete(sel[0])
        messagebox.showinfo("Deleted", "Customer deleted.")

    def manage_products(self):
        win = tk.Toplevel(self)
        win.title("Product Management")
        tree = ttk.Treeview(win, columns=('id','category','name','price'), show='headings')
        for c in ('id','category','name','price'):
            tree.heading(c, text=c.capitalize())
        tree.pack(fill='both', expand=True)
        self.load_products(tree)
        ttk.Button(win, text="Add Product", command=lambda: self.add_product(tree)).pack(side='left', padx=5)
        ttk.Button(win, text="Update Product", command=lambda: self.update_product(tree)).pack(side='left', padx=5)
        ttk.Button(win, text="Delete Product", command=lambda: self.delete_product(tree)).pack(side='left', padx=5)

    def load_products(self, tree):
        for i in tree.get_children():
            tree.delete(i)
        for p in conn.execute("SELECT * FROM products").fetchall():
            tree.insert('', 'end', values=p)

    def add_product(self, tree):
        popup = tk.Toplevel(self)
        popup.title("Add Product")
        cat = tk.StringVar(); name = tk.StringVar(); price = tk.DoubleVar()
        for txt, var in [("Category", cat), ("Name", name), ("Price", price)]:
            ttk.Label(popup, text=txt).pack(); ttk.Entry(popup, textvariable=var).pack()
        ttk.Button(popup, text="Save", command=lambda: self.save_product(cat,name,price,popup,tree)).pack(pady=5)

    def save_product(self, cat,name,price,popup,tree):
        conn.execute("INSERT INTO products (category,name,price) VALUES (?,?,?)",
                     (cat.get(),name.get(),price.get())); conn.commit()
        popup.destroy(); self.load_products(tree)

    def update_product(self, tree):
        sel = tree.selection()
        if not sel: return
        pid, cat, name, price = tree.item(sel[0])['values']
        popup = tk.Toplevel(self)
        popup.title("Update Product")
        catv = tk.StringVar(value=cat); namev = tk.StringVar(value=name); pricev = tk.DoubleVar(value=price)
        for txt, var in [("Category", catv), ("Name", namev), ("Price", pricev)]:
            ttk.Label(popup, text=txt).pack(); ttk.Entry(popup, textvariable=var).pack()
        ttk.Button(popup, text="Save", command=lambda: self.save_update(pid,catv,namev,pricev,popup,tree)).pack(pady=5)

    def save_update(self, pid,cat,name,price,popup,tree):
        conn.execute("UPDATE products SET category=?, name=?, price=? WHERE id=?",
                     (cat.get(),name.get(),price.get(),pid))
        conn.commit(); popup.destroy(); self.load_products(tree)

    def delete_product(self, tree):
        sel = tree.selection()
        if not sel: return
        pid = tree.item(sel[0])['values'][0]
        conn.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
        self.load_products(tree)

    def seed_sample_products(self, controller):
        confirm = messagebox.askyesno(
            "Confirm Seed",
            "This will delete all existing products and re-add the 10 default categories × 10 products.\n\nDo you want to continue?"
        )
        if not confirm:
            return

        # Clear existing products
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
                controller.query(
                    "INSERT INTO products (category, name, price) VALUES (?, ?, ?)",
                    (cat, name, price)
                )

        controller.conn.commit()
        messagebox.showinfo("Database Seeded", "Default products have been repopulated successfully!")
        self.refresh_products(controller)


# ---------------- ADMIN REPORTS ----------------
class AdminReportsPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Admin Reports Dashboard", font=('Helvetica',16,'bold')).pack(pady=10)
        self.filter_var = tk.StringVar(value="All Time")
        ttk.OptionMenu(self, self.filter_var, "All Time", "All Time", "Today", "This Week", "This Month").pack()
        ttk.Button(self, text="Refresh", command=lambda: self.refresh(controller)).pack()
        ttk.Button(self, text="View Chart", command=self.show_sales_chart).pack()
        ttk.Button(self, text="Export CSV", command=lambda: self.export_csv(controller)).pack()
        ttk.Button(self, text="Analytics", command=lambda: self.show_analytics(controller)).pack()
        ttk.Button(self, text="Logout", command=lambda: controller.show_frame("StartPage")).pack(pady=5)

        self.tree = ttk.Treeview(self, columns=('customer','total','timestamp'), show='headings')
        for c in ('customer','total','timestamp'):
            self.tree.heading(c, text=c.capitalize())
        self.tree.pack(fill='both', expand=True)

    def refresh(self, controller):
        date_filter = self.filter_var.get()
        clause = ""
        if date_filter == "Today":
            clause = "WHERE date(timestamp)=date('now')"
        elif date_filter == "This Week":
            clause = "WHERE date(timestamp)>=date('now','-7 day')"
        elif date_filter == "This Month":
            clause = "WHERE strftime('%Y-%m',timestamp)=strftime('%Y-%m','now')"
        rows = controller.query(f"""
            SELECT users.username, orders.total, orders.timestamp
            FROM orders JOIN users ON users.id=orders.user_id
            {clause} ORDER BY orders.timestamp DESC
        """, fetch=True)
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert('', 'end', values=r)
        self._data = rows

    def show_sales_chart(self):
        if not hasattr(self, '_data') or not self._data:
            messagebox.showwarning("No Data", "Please refresh first.")
            return
        sales_by_day = {}
        for _, total, ts in self._data:
            day = ts.split()[0]
            sales_by_day[day] = sales_by_day.get(day, 0) + total
        plt.bar(sales_by_day.keys(), sales_by_day.values())
        plt.xticks(rotation=45)
        plt.title("Sales Over Time")
        plt.show()

    def export_csv(self, controller):
        if not hasattr(self, '_data') or not self._data:
            return messagebox.showwarning("No Data", "Refresh first.")
        path = filedialog.asksaveasfilename(defaultextension='.csv')
        if not path: return
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Customer','Total','Timestamp'])
            for row in self._data:
                writer.writerow(row)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def show_analytics(self, controller):
        top_products = controller.query("""
            SELECT products.name, COUNT(*) as sold_count
            FROM orders
            JOIN users ON orders.user_id = users.id
            JOIN products ON 1=1
            GROUP BY products.name ORDER BY sold_count DESC LIMIT 5
        """, fetch=True)
        top_customers = controller.query("""
            SELECT users.username, COUNT(*) as order_count
            FROM orders
            JOIN users ON users.id = orders.user_id
            GROUP BY users.username ORDER BY order_count DESC LIMIT 5
        """, fetch=True)
        text = "Top 5 Customers:\n" + "\n".join(f"{u[0]} ({u[1]} orders)" for u in top_customers)
        text += "\n\nTop 5 Products (by frequency):\n" + "\n".join(f"{p[0]}" for p in top_products)
        messagebox.showinfo("Analytics", text)

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app = ShopApp()
    app.mainloop()
