import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import os
from functools import partial

DB_FILE = 'shop_app.db'

CATEGORIES = [f'Category {i+1}' for i in range(10)]

# --------------------------------------
# Database
# --------------------------------------

def init_db():
    new_db = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        loyalty_points INTEGER DEFAULT 0
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        name TEXT,
        price REAL,
        stock INTEGER
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        total REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()

    # seed data (users and products)
    if new_db:
        # create default admin and staff
        c.execute("INSERT OR IGNORE INTO users (username,password,role,loyalty_points) VALUES ('admin','admin','admin',0)")
        c.execute("INSERT OR IGNORE INTO users (username,password,role,loyalty_points) VALUES ('staff','staff','staff',0)")

        # seed products: 10 categories x 10 products
        for i,cat in enumerate(CATEGORIES):
            for j in range(10):
                name = f"{cat} - Product {j+1}"
                price = round(5 + (i*2) + j*1.5, 2)
                stock = 10 + j
                c.execute('INSERT INTO products (category,name,price,stock) VALUES (?,?,?,?)', (cat,name,price,stock))
        conn.commit()

    return conn

# --------------------------------------
# App
# --------------------------------------

class ShopApp(tk.Tk):
    def __init__(self, db_conn):
        super().__init__()
        self.title('Nexus Tech - Demo Shop')
        self.geometry('1000x650')
        self.db = db_conn
        self.user = None  # logged-in user dict
        self.cart = []  # list of (product_id, qty)

        container = ttk.Frame(self)
        container.pack(fill='both', expand=True)

        self.frames = {}
        for F in (StartPage, CustomerRegisterPage, CustomerLoginPage, StaffLoginPage,
                  CustomerAccountPage, ShoppingPage, StaffManagePage, AdminReportsPage):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky='nsew')

        self.show_frame('StartPage')

    def show_frame(self, name):
        frame = self.frames[name]
        frame.event_generate('<<ShowFrame>>')
        frame.tkraise()

    def query(self, sql, params=(), fetch=False, many=False):
        c = self.db.cursor()
        if many:
            c.executemany(sql, params)
            self.db.commit()
            return None
        else:
            c.execute(sql, params)
            if fetch:
                return c.fetchall()
            else:
                self.db.commit()
                return c

    def login(self, username, password):
        row = self.query('SELECT id,username,role,loyalty_points FROM users WHERE username=? AND password=?', (username,password), fetch=True)
        if row:
            uid, uname, role, lp = row[0]
            self.user = {'id':uid,'username':uname,'role':role,'loyalty_points':lp}
            return True
        return False

    def logout(self):
        self.user = None
        self.cart = []
        self.show_frame('StartPage')

# --------------------------------------
# Pages
# --------------------------------------

class StartPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        lbl = ttk.Label(self, text='Welcome to Nexus Tech - Demo Shop', font=('Helvetica', 18))
        lbl.pack(pady=20)

        btn_customer_login = ttk.Button(self, text='Customer Login', command=lambda: controller.show_frame('CustomerLoginPage'))
        btn_customer_register = ttk.Button(self, text='Customer Register', command=lambda: controller.show_frame('CustomerRegisterPage'))
        btn_shopping = ttk.Button(self, text='Shopping (Guest)', command=lambda: controller.show_frame('ShoppingPage'))
        btn_staff_login = ttk.Button(self, text='Staff Login', command=lambda: controller.show_frame('StaffLoginPage'))
        btn_admin = ttk.Button(self, text='Admin Reports', command=lambda: controller.show_frame('AdminReportsPage'))

        for w in (btn_customer_login, btn_customer_register, btn_shopping, btn_staff_login, btn_admin):
            w.pack(pady=6)

class CustomerRegisterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text='Customer Registration', font=('Helvetica',16)).pack(pady=10)
        frm = ttk.Frame(self)
        frm.pack()
        ttk.Label(frm, text='Username:').grid(row=0,column=0,sticky='e')
        self.username = ttk.Entry(frm)
        self.username.grid(row=0,column=1)
        ttk.Label(frm, text='Password:').grid(row=1,column=0,sticky='e')
        self.password = ttk.Entry(frm, show='*')
        self.password.grid(row=1,column=1)

        ttk.Button(self, text='Register', command=lambda: self.register(controller)).pack(pady=10)
        ttk.Button(self, text='Back', command=lambda: controller.show_frame('StartPage')).pack()

    def register(self, controller):
        u = self.username.get().strip()
        p = self.password.get().strip()
        if not u or not p:
            messagebox.showwarning('Error','Enter username and password')
            return
        try:
            controller.query('INSERT INTO users (username,password,role,loyalty_points) VALUES (?,?,"customer",0)', (u,p))
            messagebox.showinfo('OK','Registered. You can login now.')
            controller.show_frame('CustomerLoginPage')
        except sqlite3.IntegrityError:
            messagebox.showerror('Error','Username already exists')

class CustomerLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text='Customer Login', font=('Helvetica',16)).pack(pady=10)
        frm = ttk.Frame(self)
        frm.pack()
        ttk.Label(frm, text='Username:').grid(row=0,column=0,sticky='e')
        self.username = ttk.Entry(frm)
        self.username.grid(row=0,column=1)
        ttk.Label(frm, text='Password:').grid(row=1,column=0,sticky='e')
        self.password = ttk.Entry(frm, show='*')
        self.password.grid(row=1,column=1)

        ttk.Button(self, text='Login', command=lambda: self.login(controller)).pack(pady=10)
        ttk.Button(self, text='Back', command=lambda: controller.show_frame('StartPage')).pack()

    def login(self, controller):
        u = self.username.get().strip()
        p = self.password.get().strip()
        if controller.login(u,p):
            if controller.user['role'] != 'customer':
                messagebox.showwarning('Not allowed','This login is not a customer account')
                controller.logout()
                return
            messagebox.showinfo('OK','Logged in')
            controller.show_frame('CustomerAccountPage')
        else:
            messagebox.showerror('Error','Invalid credentials')

class StaffLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text='Staff Login', font=('Helvetica',16)).pack(pady=10)
        frm = ttk.Frame(self)
        frm.pack()
        ttk.Label(frm, text='Username:').grid(row=0,column=0,sticky='e')
        self.username = ttk.Entry(frm)
        self.username.grid(row=0,column=1)
        ttk.Label(frm, text='Password:').grid(row=1,column=0,sticky='e')
        self.password = ttk.Entry(frm, show='*')
        self.password.grid(row=1,column=1)

        ttk.Button(self, text='Login', command=lambda: self.login(controller)).pack(pady=10)
        ttk.Button(self, text='Back', command=lambda: controller.show_frame('StartPage')).pack()

    def login(self, controller):
        u = self.username.get().strip()
        p = self.password.get().strip()
        if controller.login(u,p):
            if controller.user['role'] not in ('staff','admin'):
                messagebox.showwarning('Not allowed','This login is not staff/admin')
                controller.logout()
                return
            messagebox.showinfo('OK','Logged in')
            controller.show_frame('StaffManagePage')
        else:
            messagebox.showerror('Error','Invalid credentials')

class CustomerAccountPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Customer Account', font=('Helvetica',16)).pack(pady=10)
        self.lbl_user = ttk.Label(self, text='')
        self.lbl_user.pack()
        self.lbl_points = ttk.Label(self, text='')
        self.lbl_points.pack()

        ttk.Button(self, text='Go Shopping', command=lambda: controller.show_frame('ShoppingPage')).pack(pady=6)
        ttk.Button(self, text='Logout', command=lambda: controller.logout()).pack()

        self.bind('<<ShowFrame>>', self.refresh)

    def refresh(self, event=None):
        user = self.controller.user
        if not user:
            messagebox.showinfo('Info','Not logged in')
            self.controller.show_frame('StartPage')
            return
        self.lbl_user.config(text=f"Username: {user['username']}")
        # fetch loyalty points freshly
        row = self.controller.query('SELECT loyalty_points FROM users WHERE id=?', (user['id'],), fetch=True)
        if row:
            pts = row[0][0]
            self.lbl_points.config(text=f'Loyalty Points: {pts}')
            self.controller.user['loyalty_points'] = pts

class ShoppingPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Shopping', font=('Helvetica',16)).pack(pady=8)
        topfrm = ttk.Frame(self)
        topfrm.pack(fill='x')
        ttk.Button(topfrm, text='View Cart', command=self.view_cart).pack(side='right', padx=6)
        ttk.Button(topfrm, text='Back to Start', command=lambda: controller.show_frame('StartPage')).pack(side='left')

        content = ttk.Frame(self)
        content.pack(fill='both', expand=True, padx=8, pady=8)

        # left: categories
        left = ttk.Frame(content)
        left.pack(side='left', fill='y')
        ttk.Label(left, text='Categories').pack()
        self.cat_list = tk.Listbox(left, height=20)
        self.cat_list.pack()
        for c in CATEGORIES:
            self.cat_list.insert('end', c)
        self.cat_list.bind('<<ListboxSelect>>', self.show_products)

        # right: products
        right = ttk.Frame(content)
        right.pack(side='left', fill='both', expand=True)
        self.products_tree = ttk.Treeview(right, columns=('id','name','price','stock'), show='headings')
        for col in ('id','name','price','stock'):
            self.products_tree.heading(col, text=col.title())
        self.products_tree.pack(fill='both', expand=True)

        btnfrm = ttk.Frame(right)
        btnfrm.pack(fill='x')
        ttk.Button(btnfrm, text='Add Selected to Cart', command=self.add_to_cart).pack(side='left', padx=6)
        ttk.Button(btnfrm, text='Checkout', command=self.checkout).pack(side='left', padx=6)

        self.bind('<<ShowFrame>>', lambda e: self.refresh())

    def refresh(self):
        # show all products by default
        self.show_products()

    def show_products(self, event=None):
        sel = self.cat_list.curselection()
        if sel:
            cat = self.cat_list.get(sel[0])
            rows = self.controller.query('SELECT id,name,price,stock FROM products WHERE category=?', (cat,), fetch=True)
        else:
            rows = self.controller.query('SELECT id,name,price,stock FROM products', (), fetch=True)
        for i in self.products_tree.get_children():
            self.products_tree.delete(i)
        for r in rows:
            self.products_tree.insert('', 'end', values=r)

    def add_to_cart(self):
        sel = self.products_tree.selection()
        if not sel:
            messagebox.showwarning('Select','Select a product')
            return
        vals = self.products_tree.item(sel[0])['values']
        pid = vals[0]
        qty = simpledialog.askinteger('Quantity','Quantity to add',minvalue=1,initialvalue=1)
        if qty:
            # append to cart
            self.controller.cart.append((pid, qty))
            messagebox.showinfo('Added','Added to cart')

    def view_cart(self):
        if not self.controller.cart:
            messagebox.showinfo('Cart','Cart is empty')
            return
        top = tk.Toplevel(self)
        top.title('Cart')
        tree = ttk.Treeview(top, columns=('pid','name','qty','price','subtotal'), show='headings')
        for col in ('pid','name','qty','price','subtotal'):
            tree.heading(col, text=col.title())
        tree.pack(fill='both', expand=True)
        total = 0.0
        for pid,qty in self.controller.cart:
            row = self.controller.query('SELECT name,price FROM products WHERE id=?', (pid,), fetch=True)
            if not row: continue
            name,price = row[0]
            subtotal = price * qty
            total += subtotal
            tree.insert('', 'end', values=(pid,name,qty,price,round(subtotal,2)))
        ttk.Label(top, text=f'Total: {round(total,2)}').pack()

    def checkout(self):
        if not self.controller.cart:
            messagebox.showwarning('Empty','Cart is empty')
            return
        if not self.controller.user or self.controller.user['role']!='customer':
            if not messagebox.askyesno('Guest checkout','You are not logged in as customer. Continue as guest?'):
                return
            user_id = None
        else:
            user_id = self.controller.user['id']

        total = 0.0
        for pid,qty in self.controller.cart:
            row = self.controller.query('SELECT price,stock FROM products WHERE id=?', (pid,), fetch=True)
            if not row:
                messagebox.showerror('Error','Product not found')
                return
            price,stock = row[0]
            if qty > stock:
                messagebox.showerror('Error',f'Not enough stock for product id {pid}')
                return
            total += price*qty

        # reduce stock
        for pid,qty in self.controller.cart:
            self.controller.query('UPDATE products SET stock = stock - ? WHERE id=?', (qty,pid))

        # create order
        self.controller.query('INSERT INTO orders (user_id,total) VALUES (?,?)', (user_id, total))

        # award loyalty points if customer
        if user_id:
            points = int(total // 10)  # 1 point per $10 spent
            self.controller.query('UPDATE users SET loyalty_points = loyalty_points + ? WHERE id=?', (points, user_id))
            messagebox.showinfo('Thank you', f'Order placed. You earned {points} loyalty points.')
        else:
            messagebox.showinfo('Thank you', 'Order placed (guest).')

        self.controller.cart = []
        # refresh account page if open
        self.controller.show_frame('ShoppingPage')

class StaffManagePage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Staff Management', font=('Helvetica',16)).pack(pady=8)
        topfrm = ttk.Frame(self)
        topfrm.pack(fill='x')
        ttk.Button(topfrm, text='Logout', command=lambda: controller.logout()).pack(side='right')
        ttk.Button(topfrm, text='Back to Start', command=lambda: controller.show_frame('StartPage')).pack(side='left')

        mid = ttk.Frame(self)
        mid.pack(fill='both', expand=True)

        # Products tree
        left = ttk.Frame(mid)
        left.pack(side='left', fill='both', expand=True, padx=6, pady=6)
        ttk.Label(left, text='Products').pack()
        self.tree = ttk.Treeview(left, columns=('id','category','name','price','stock'), show='headings')
        for col in ('id','category','name','price','stock'):
            self.tree.heading(col, text=col.title())
        self.tree.pack(fill='both', expand=True)

        btns = ttk.Frame(left)
        btns.pack(fill='x')
        ttk.Button(btns, text='Add Product', command=self.add_product).pack(side='left')
        ttk.Button(btns, text='Edit Selected', command=self.edit_selected).pack(side='left')
        ttk.Button(btns, text='Delete Selected', command=self.delete_selected).pack(side='left')

        # Customers list
        right = ttk.Frame(mid)
        right.pack(side='left', fill='y', padx=6, pady=6)
        ttk.Label(right, text='Customers').pack()
        self.cust_tree = ttk.Treeview(right, columns=('id','username','points'), show='headings', height=15)
        for col in ('id','username','points'):
            self.cust_tree.heading(col, text=col.title())
        self.cust_tree.pack()
        ttk.Button(right, text='Refresh', command=self.refresh).pack(pady=6)

        self.bind('<<ShowFrame>>', lambda e: self.refresh())

    def refresh(self):
        # products
        rows = self.controller.query('SELECT id,category,name,price,stock FROM products', (), fetch=True)
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in rows:
            self.tree.insert('', 'end', values=r)
        # customers
        rows = self.controller.query("SELECT id,username,loyalty_points FROM users WHERE role='customer'", (), fetch=True)
        for i in self.cust_tree.get_children(): self.cust_tree.delete(i)
        for r in rows:
            self.cust_tree.insert('', 'end', values=r)

    def add_product(self):
        dlg = ProductDialog(self, title='Add Product')
        self.wait_window(dlg)
        if dlg.result:
            cat,name,price,stock = dlg.result
            self.controller.query('INSERT INTO products (category,name,price,stock) VALUES (?,?,?,?)', (cat,name,price,stock))
            self.refresh()

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Select','Select a product')
            return
        vals = self.tree.item(sel[0])['values']
        pid = vals[0]
        dlg = ProductDialog(self, title='Edit Product', initial=vals)
        self.wait_window(dlg)
        if dlg.result:
            cat,name,price,stock = dlg.result
            self.controller.query('UPDATE products SET category=?,name=?,price=?,stock=? WHERE id=?', (cat,name,price,stock,pid))
            self.refresh()

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Select','Select a product')
            return
        vals = self.tree.item(sel[0])['values']
        pid = vals[0]
        if messagebox.askyesno('Confirm','Delete product?'):
            self.controller.query('DELETE FROM products WHERE id=?', (pid,))
            self.refresh()

class ProductDialog(tk.Toplevel):
    def __init__(self, parent, title='Product', initial=None):
        super().__init__(parent)
        self.title(title)
        self.result = None
        frm = ttk.Frame(self)
        frm.pack(padx=8,pady=8)
        ttk.Label(frm, text='Category').grid(row=0,column=0)
        self.cat = ttk.Combobox(frm, values=CATEGORIES)
        self.cat.grid(row=0,column=1)
        ttk.Label(frm, text='Name').grid(row=1,column=0)
        self.name = ttk.Entry(frm)
        self.name.grid(row=1,column=1)
        ttk.Label(frm, text='Price').grid(row=2,column=0)
        self.price = ttk.Entry(frm)
        self.price.grid(row=2,column=1)
        ttk.Label(frm, text='Stock').grid(row=3,column=0)
        self.stock = ttk.Entry(frm)
        self.stock.grid(row=3,column=1)

        if initial:
            # id,category,name,price,stock
            self.cat.set(initial[1])
            self.name.insert(0, initial[2])
            self.price.insert(0, str(initial[3]))
            self.stock.insert(0, str(initial[4]))

        ttk.Button(self, text='OK', command=self.on_ok).pack(pady=6)

    def on_ok(self):
        try:
            cat = self.cat.get().strip()
            name = self.name.get().strip()
            price = float(self.price.get())
            stock = int(self.stock.get())
            if not cat or not name:
                raise ValueError('Missing')
            self.result = (cat,name,price,stock)
            self.destroy()
        except Exception as e:
            messagebox.showerror('Error', f'Invalid data: {e}')

class AdminReportsPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Admin Reports', font=('Helvetica',16)).pack(pady=8)
        top = ttk.Frame(self)
        top.pack(fill='x')
        ttk.Button(top, text='Back to Start', command=lambda: controller.show_frame('StartPage')).pack(side='left')
        ttk.Button(top, text='Refresh', command=self.refresh).pack(side='left')
        ttk.Button(top, text='Logout', command=lambda: controller.logout()).pack(side='right')

        self.txt = tk.Text(self, height=20)
        self.txt.pack(fill='both', expand=True, padx=8, pady=8)

        self.bind('<<ShowFrame>>', lambda e: self.refresh())

    def refresh(self):
        # basic reports: total sales, sales by product, top customers
        rows = self.controller.query('SELECT SUM(total) FROM orders', (), fetch=True)
        total_sales = rows[0][0] if rows and rows[0][0] is not None else 0.0
        rows = self.controller.query('SELECT p.name, SUM(o.total) FROM orders o JOIN products p ON 1=1 WHERE 1=0', (), fetch=True)
        # simpler: count orders
        orders = self.controller.query('SELECT COUNT(*) FROM orders', (), fetch=True)[0][0]
        top_customers = self.controller.query('SELECT username, loyalty_points FROM users WHERE role="customer" ORDER BY loyalty_points DESC LIMIT 10', (), fetch=True)

        self.txt.delete('1.0','end')
        self.txt.insert('end', f'Total Sales (sum of order totals): {total_sales}\n')
        self.txt.insert('end', f'Number of Orders: {orders}\n\n')
        self.txt.insert('end', 'Top Customers by Loyalty Points:\n')
        for u,pts in top_customers:
            self.txt.insert('end', f' - {u}: {pts} pts\n')

# --------------------------------------
# Run
# --------------------------------------

if __name__ == '__main__':
    conn = init_db()
    app = ShopApp(conn)
    app.mainloop()
