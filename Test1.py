import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3
from datetime import datetime
import csv
import os
import matplotlib.pyplot as plt
from functools import partial

DB_NAME = 'shop_system.db'
DB_FILE = 'shop_app.db'

# ====================== DATABASE SETUP ==========================
def init_db():
    new_db = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        card_number TEXT,
        card_expiry TEXT,
        card_cvv TEXT,
        loyalty_points INTEGER DEFAULT 0
    )''')

    # Products Table
    c.execute('''CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        price REAL
    )''')

    # Orders Table
    c.execute('''CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        total REAL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Order Products Table
    c.execute('''CREATE TABLE IF NOT EXISTS order_products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER
    )''')

    conn.commit()

    
    if new_db:
        # Default system users
        default_users = [
            ('admin', 'admin', 'admin', 0),
            ('Admin', 'admin123', 'admin', 0),  # Requested new admin account
            ('staff', 'staff', 'staff', 0)
        ]
        for u, p, r, l in default_users:
            try:
                c.execute("INSERT INTO users (username,password,role,loyalty_points) VALUES (?,?,?,?)", (u,p,r,l))
            except sqlite3.IntegrityError:
                pass

        # Insert demo products
        for i,cat in enumerate(CATEGORIES):
            for j in range(10):
                name = f"{cat} - Product {j+1}"
                price = round(5 + (i*2) + j*1.5, 2)
                stock = 10 + j
                c.execute('INSERT INTO products (category,name,price,stock) VALUES (?,?,?,?)', (cat,name,price,stock))
        conn.commit()

    return conn

    # Seed products if not exists
    c.execute('SELECT COUNT(*) FROM products')
    if c.fetchone()[0] == 0:
        for cat in range(1, 11):
            for p in range(1, 11):
                c.execute('INSERT INTO products (name, category, price) VALUES (?, ?, ?)',
                          (f'Product {p}', f'Category {cat}', round(10 + p * 1.5, 2)))
    conn.commit()
    conn.close()


# ====================== MAIN APPLICATION ==========================
class ShopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tech Shop System")
        self.geometry("1000x700")

        init_db()
        self.current_user = None

        container = ttk.Frame(self)
        container.pack(fill='both', expand=True)

        self.frames = {}
        for F in (StartPage, CustomerRegisterPage, CustomerLoginPage, StaffLoginPage,
                  CustomerAccountPage, ShoppingPage, StaffPage, AdminReportsPage):
            page_name = F.__name__
            frame = F(container, self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky='nsew')

        self.show_frame("StartPage")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "refresh"):
            frame.refresh(self)

    def query(self, query, params=(), fetch=False):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(query, params)
        result = c.fetchall() if fetch else None
        conn.commit()
        conn.close()
        return result

    def logout(self):
        self.current_user = None
        self.show_frame("StartPage")


# ====================== START PAGE ==========================
class StartPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Welcome to Nexus Tech Shop", font=('Helvetica', 20, 'bold')).pack(pady=30)

        ttk.Button(self, text="Customer Login", command=lambda: controller.show_frame("CustomerLoginPage")).pack(pady=10)
        ttk.Button(self, text="Customer Registration", command=lambda: controller.show_frame("CustomerRegisterPage")).pack(pady=10)
        ttk.Button(self, text="Staff Login", command=lambda: controller.show_frame("StaffLoginPage")).pack(pady=10)
        ttk.Button(self, text="Admin Login", command=lambda: controller.show_frame("AdminReportsPage")).pack(pady=10)


# ====================== CUSTOMER REGISTRATION ==========================
class CustomerRegisterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Customer Registration", font=('Helvetica', 16, 'bold')).pack(pady=20)

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.card_number = tk.StringVar()
        self.card_expiry = tk.StringVar()
        self.card_cvv = tk.StringVar()

        fields = [
            ("Username:", self.username),
            ("Password:", self.password),
            ("Card Number:", self.card_number),
            ("Card Expiry (MM/YY):", self.card_expiry),
            ("Card CVV:", self.card_cvv)
        ]

        for label, var in fields:
            ttk.Label(self, text=label).pack()
            ttk.Entry(self, textvariable=var, show="*" if 'Password' in label or 'CVV' in label else None).pack()

        ttk.Button(self, text="Register", command=lambda: self.register(controller)).pack(pady=10)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def register(self, controller):
        u, p = self.username.get(), self.password.get()
        cn, ce, cvv = self.card_number.get(), self.card_expiry.get(), self.card_cvv.get()
        if not (u and p and cn and ce and cvv):
            messagebox.showerror("Error", "All fields required.")
            return
        try:
            controller.query('INSERT INTO users (username, password, role, card_number, card_expiry, card_cvv) VALUES (?, ?, ?, ?, ?, ?)',
                             (u, p, 'customer', cn, ce, cvv))
            messagebox.showinfo("Success", "Registration successful!")
            controller.show_frame("CustomerLoginPage")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists.")


# ====================== CUSTOMER LOGIN ==========================
class CustomerLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Customer Login", font=('Helvetica', 16, 'bold')).pack(pady=20)

        self.username = tk.StringVar()
        self.password = tk.StringVar()

        ttk.Label(self, text="Username:").pack()
        ttk.Entry(self, textvariable=self.username).pack()
        ttk.Label(self, text="Password:").pack()
        ttk.Entry(self, textvariable=self.password, show="*").pack()

        ttk.Button(self, text="Login", command=lambda: self.login(controller)).pack(pady=10)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def login(self, controller):
        u, p = self.username.get(), self.password.get()
        user = controller.query('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, 'customer'), fetch=True)
        if user:
            controller.current_user = user[0]
            controller.show_frame("CustomerAccountPage")
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")


# ====================== STAFF LOGIN ==========================
class StaffLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Staff Login", font=('Helvetica', 16, 'bold')).pack(pady=20)

        self.username = tk.StringVar()
        self.password = tk.StringVar()

        ttk.Label(self, text="Username:").pack()
        ttk.Entry(self, textvariable=self.username).pack()
        ttk.Label(self, text="Password:").pack()
        ttk.Entry(self, textvariable=self.password, show="*").pack()

        ttk.Button(self, text="Login", command=lambda: self.login(controller)).pack(pady=10)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack()

    def login(self, controller):
        u, p = self.username.get(), self.password.get()
        if u == "Admin" and p == "admin123":
            controller.show_frame("AdminReportsPage")
        else:
            messagebox.showerror("Access Denied", "Invalid admin credentials.")


# ====================== CUSTOMER ACCOUNT PAGE ==========================
class CustomerAccountPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.points_label = ttk.Label(self, text="")
        ttk.Label(self, text="Customer Account", font=('Helvetica', 16, 'bold')).pack(pady=20)
        self.points_label.pack(pady=10)
        ttk.Button(self, text="Go to Shopping", command=lambda: controller.show_frame("ShoppingPage")).pack(pady=5)
        ttk.Button(self, text="Logout", command=lambda: controller.logout()).pack(pady=5)

    def refresh(self, controller):
        if controller.current_user:
            user_id = controller.current_user[0]
            points = controller.query('SELECT loyalty_points FROM users WHERE id=?', (user_id,), fetch=True)[0][0]
            self.points_label.config(text=f"Loyalty Points: {points}")


# ====================== SHOPPING PAGE ==========================
class ShoppingPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Shopping Page', font=('Helvetica',16)).pack(pady=8)
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

        self.tree = ttk.Treeview(mid, columns=('id','name','price','stock'), show='headings')
        for col in ('id','name','price','stock'):
            self.tree.heading(col, text=col.title())
        self.tree.pack(side='left', fill='both', expand=True)

        bottom = ttk.Frame(self)
        bottom.pack(fill='x')
        ttk.Button(bottom, text='Add to Cart', command=self.add_to_cart).pack(side='left', padx=4)
        ttk.Button(bottom, text='Checkout', command=self.checkout).pack(side='left', padx=4)
        self.total_label = ttk.Label(bottom, text='Total: $0.00')
        self.total_label.pack(side='right')

        self.bind('<<ShowFrame>>', lambda e: self.refresh())

    def refresh(self):
        self.show_products()
        self.update_total()

    def show_products(self, event=None):
        sel = self.cat_list.curselection()
        if sel:
            cat = self.cat_list.get(sel[0])
            rows = self.controller.query('SELECT id,name,price,stock FROM products WHERE category=?',(cat,),fetch=True)
        else:
            rows = self.controller.query('SELECT id,name,price,stock FROM products',fetch=True)
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in rows:
            self.tree.insert('', 'end', values=r)

    def add_to_cart(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Select','Select an item')
            return
        vals = self.tree.item(sel[0])['values']
        qty = simpledialog.askinteger('Quantity','Enter quantity',minvalue=1,initialvalue=1)
        if qty:
            self.controller.cart.append((vals[0],qty))
            self.update_total()

    def update_total(self):
        total = 0.0
        for pid,qty in self.controller.cart:
            price = self.controller.query('SELECT price FROM products WHERE id=?',(pid,),fetch=True)[0][0]
            total += price*qty
        self.total_label.config(text=f'Total: ${round(total,2)}')

    def view_cart(self):
        if not self.controller.cart:
            messagebox.showinfo('Cart','Cart is empty')
            return
        top = tk.Toplevel(self)
        top.title('Cart Details')
        tree = ttk.Treeview(top, columns=('name','qty','price','subtotal'), show='headings')
        for c in ('name','qty','price','subtotal'):
            tree.heading(c, text=c.title())
        tree.pack(fill='both', expand=True)
        total = 0
        for pid,qty in self.controller.cart:
            n,p = self.controller.query('SELECT name,price FROM products WHERE id=?',(pid,),fetch=True)[0]
            sub=p*qty
            total+=sub
            tree.insert('', 'end', values=(n,qty,p,round(sub,2)))
        ttk.Label(top, text=f'Total: ${round(total,2)}').pack()

    def checkout(self):
        if not self.controller.cart:
            messagebox.showinfo('Empty','Cart is empty')
            return
        total = sum(self.controller.query('SELECT price FROM products WHERE id=?',(pid,),fetch=True)[0][0]*qty for pid,qty in self.controller.cart)
        u = self.controller.user
        if not u or u['role']!='customer':
            messagebox.showinfo('Guest','You must be logged in to pay with card.')
            return
        if not u['card_number']:
            messagebox.showwarning('No Card','Add a card in your account first.')
            return
        confirm = messagebox.askyesno('Payment', f'Charge ${round(total,2)} to card ending {u["card_number"][-4:]}?')
        if not confirm:
            return
        # simulate deduction
        messagebox.showinfo('Payment','Payment successful (simulated).')
        self.controller.query('INSERT INTO orders (user_id,total) VALUES (?,?)',(u['id'],total))
        points = int(total//10)
        self.controller.query('UPDATE users SET loyalty_points = loyalty_points + ? WHERE id=?',(points,u['id']))
        self.controller.cart.clear()
        self.update_total()
        messagebox.showinfo('Done',f'Order completed, earned {points} loyalty points.')


# ====================== STAFF PAGE ==========================
class StaffPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text="Staff Management", font=('Helvetica', 16, 'bold')).pack(pady=20)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame("StartPage")).pack(pady=10)


# ====================== ADMIN REPORTS + ANALYTICS ==========================
class AdminReportsPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Admin Dashboard', font=('Helvetica', 16, 'bold')).pack(pady=10)

        self.tabs = ttk.Notebook(self)
        self.report_tab = ttk.Frame(self.tabs)
        self.analytics_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.report_tab, text='Reports')
        self.tabs.add(self.analytics_tab, text='Analytics')
        self.tabs.pack(fill='both', expand=True)

        # REPORTS TAB
        self.build_reports_tab()
        # ANALYTICS TAB
        self.build_analytics_tab()

    def build_reports_tab(self):
        page = self.report_tab
        ttk.Button(page, text="Back", command=lambda: self.controller.show_frame("StartPage")).pack(pady=5)
        ttk.Button(page, text="Logout", command=lambda: self.controller.logout()).pack(pady=5)

        self.filter_var = tk.StringVar(value='All Time')
        ttk.Label(page, text='Filter by:').pack()
        ttk.OptionMenu(page, self.filter_var, 'All Time', 'All Time', 'Today', 'This Week', 'This Month').pack()
        ttk.Button(page, text="Apply Filter", command=self.refresh).pack(pady=5)

        self.summary_lbl = ttk.Label(page, text="")
        self.summary_lbl.pack(pady=5)

        self.tree = ttk.Treeview(page, columns=('username', 'total', 'timestamp'), show='headings')
        for col in ('username', 'total', 'timestamp'):
            self.tree.heading(col, text=col.title())
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)

        ttk.Button(page, text="View Sales Chart", command=self.show_sales_chart).pack(pady=5)
        ttk.Button(page, text="Export CSV", command=self.export_csv).pack(pady=5)

    def build_analytics_tab(self):
        page = self.analytics_tab
        ttk.Label(page, text='Analytics Dashboard', font=('Helvetica', 14, 'bold')).pack(pady=10)
        ttk.Button(page, text="Top 5 Products", command=self.show_top_products).pack(pady=5)
        ttk.Button(page, text="Top 5 Customers", command=self.show_top_customers).pack(pady=5)

    def refresh(self, *_):
        f = self.filter_var.get()
        clause = ""
        if f == 'Today':
            clause = "WHERE date(timestamp)=date('now')"
        elif f == 'This Week':
            clause = "WHERE date(timestamp)>=date('now','-7 day')"
        elif f == 'This Month':
            clause = "WHERE strftime('%Y-%m',timestamp)=strftime('%Y-%m','now')"

        rows = self.controller.query(f"""
            SELECT u.username, o.total, o.timestamp
            FROM orders o
            JOIN users u ON u.id=o.user_id
            {clause}
            ORDER BY o.timestamp DESC
        """, fetch=True)

        for i in self.tree.get_children():
            self.tree.delete(i)
        total = 0
        for r in rows:
            self.tree.insert('', 'end', values=r)
            total += r[1]
        self.summary_lbl.config(text=f"Orders: {len(rows)} | Total Sales: ${total:.2f}")
        self._data = rows

    def export_csv(self):
        if not hasattr(self, "_data"):
            messagebox.showerror("Error", "No data to export.")
            return
        file = filedialog.asksaveasfilename(defaultextension=".csv")
        if not file:
            return
        with open(file, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(["Customer", "Total", "Timestamp"])
            for row in self._data:
                w.writerow(row)
        messagebox.showinfo("Export", f"Data exported to {file}")

    def show_sales_chart(self):
        if not hasattr(self, "_data"):
            messagebox.showerror("Error", "No data to chart.")
            return
        sales = {}
        for _, total, ts in self._data:
            d = ts.split()[0]
            sales[d] = sales.get(d, 0) + total
        plt.bar(list(sales.keys()), list(sales.values()))
        plt.xticks(rotation=45)
        plt.title("Sales Over Time")
        plt.tight_layout()
        plt.show()

    def show_top_products(self):
        q = """
            SELECT p.name, SUM(op.quantity)
            FROM order_products op
            JOIN products p ON p.id=op.product_id
            GROUP BY p.id
            ORDER BY SUM(op.quantity) DESC
            LIMIT 5
        """
        data = self.controller.query(q, fetch=True)
        if not data:
            messagebox.showinfo("No Data", "No product data available.")
            return
        names, totals = zip(*data)
        plt.barh(names[::-1], totals[::-1])
        plt.title("Top 5 Best-Selling Products")
        plt.show()

    def show_top_customers(self):
        q = """
            SELECT u.username, COUNT(o.id)
            FROM orders o
            JOIN users u ON u.id=o.user_id
            GROUP BY u.id
            ORDER BY COUNT(o.id) DESC
            LIMIT 5
        """
        data = self.controller.query(q, fetch=True)
        if not data:
            messagebox.showinfo("No Data", "No customer data available.")
            return
        names, totals = zip(*data)
        plt.barh(names[::-1], totals[::-1])
        plt.title("Top 5 Active Customers")
        plt.show()


# ====================== RUN APP ==========================
if __name__ == "__main__":
    app = ShopApp()
    app.mainloop()
