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
        loyalty_points INTEGER DEFAULT 0,
        card_number TEXT
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

# --------------------------------------
# App Class
# --------------------------------------

class ShopApp(tk.Tk):
    def __init__(self, db_conn):
        super().__init__()
        self.title('Nexus Tech - Demo Shop')
        self.geometry('1000x650')
        self.db = db_conn
        self.user = None
        self.cart = []

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

    def query(self, sql, params=(), fetch=False):
        c = self.db.cursor()
        c.execute(sql, params)
        if fetch:
            return c.fetchall()
        self.db.commit()
        return None

    def login(self, username, password):
        username = username.strip()
        password = password.strip()
        user = self.query('SELECT id,username,role,loyalty_points,card_number,password FROM users WHERE username=?', (username,), fetch=True)

        if not user:
            return 'username'  # username not found
        uid, uname, role, lp, card, stored_pw = user[0]
        if stored_pw != password:
            return 'password'  # password incorrect
        self.user = {'id': uid, 'username': uname, 'role': role, 'loyalty_points': lp, 'card_number': card}
        return 'success'

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
        ttk.Label(self, text='Welcome to Nexus Tech - Demo Shop', font=('Helvetica', 18)).pack(pady=20)
        for txt, page in [
            ('Customer Login','CustomerLoginPage'),
            ('Customer Register','CustomerRegisterPage'),
            ('Shopping (Guest)','ShoppingPage'),
            ('Staff Login','StaffLoginPage'),
            ('Admin Reports','AdminReportsPage')
        ]:
            ttk.Button(self, text=txt, command=lambda p=page: controller.show_frame(p)).pack(pady=6)


class CustomerRegisterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text='Customer Registration', font=('Helvetica',16)).pack(pady=10)
        frm = ttk.Frame(self)
        frm.pack()
        ttk.Label(frm, text='Username:').grid(row=0,column=0)
        self.username = ttk.Entry(frm)
        self.username.grid(row=0,column=1)
        ttk.Label(frm, text='Password:').grid(row=1,column=0)
        self.password = ttk.Entry(frm, show='*')
        self.password.grid(row=1,column=1)
        ttk.Button(self, text='Register', command=lambda: self.register(controller)).pack(pady=10)
        ttk.Button(self, text='Back', command=lambda: controller.show_frame('StartPage')).pack()

    def register(self, controller):
        u,p = self.username.get().strip(), self.password.get().strip()
        if not u or not p:
            messagebox.showwarning('Error','Fill all fields')
            return
        try:
            controller.query('INSERT INTO users (username,password,role,loyalty_points) VALUES (?,?,\"customer\",0)', (u,p))
            messagebox.showinfo('OK','Registered successfully')
            controller.show_frame('CustomerLoginPage')
        except sqlite3.IntegrityError:
            messagebox.showerror('Error','Username already exists')


class CustomerLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text='Customer Login', font=('Helvetica',16)).pack(pady=10)
        frm = ttk.Frame(self)
        frm.pack()
        ttk.Label(frm, text='Username:').grid(row=0,column=0)
        self.username = ttk.Entry(frm)
        self.username.grid(row=0,column=1)
        ttk.Label(frm, text='Password:').grid(row=1,column=0)
        self.password = ttk.Entry(frm, show='*')
        self.password.grid(row=1,column=1)
        ttk.Button(self, text='Login', command=lambda: self.login(controller)).pack(pady=10)
        ttk.Button(self, text='Back', command=lambda: controller.show_frame('StartPage')).pack()

    def login(self, controller):
        result = controller.login(self.username.get(), self.password.get())
        if result == 'username':
            messagebox.showerror('Error', 'Username not found. Please check or register.')
        elif result == 'password':
            messagebox.showerror('Error', 'Incorrect password. Please try again.')
        elif result == 'success':
            if controller.user['role'] != 'customer':
                messagebox.showwarning('Error','Not a customer account')
                controller.logout()
                return
            controller.show_frame('CustomerAccountPage')
        else:
            messagebox.showerror('Error','Login failed unexpectedly.')

# (other pages remain unchanged — same as your last version)
# Keep StaffLoginPage, StaffManagePage, ShoppingPage, CustomerAccountPage, AdminReportsPage as before





class StaffLoginPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text='Staff Login', font=('Helvetica',16)).pack(pady=10)
        frm=ttk.Frame(self); frm.pack()
        ttk.Label(frm,text='Username').grid(row=0,column=0)
        self.username=ttk.Entry(frm); self.username.grid(row=0,column=1)
        ttk.Label(frm,text='Password').grid(row=1,column=0)
        self.password=ttk.Entry(frm,show='*'); self.password.grid(row=1,column=1)
        ttk.Button(self,text='Login',command=lambda:self.login(controller)).pack(pady=10)
        ttk.Button(self,text='Back',command=lambda:controller.show_frame('StartPage')).pack()

    def login(self,controller):
        if controller.login(self.username.get(),self.password.get()):
            if controller.user['role'] not in ('staff','admin'):
                messagebox.showerror('Denied','Not staff or admin')
                controller.logout()
                return
            controller.show_frame('StaffManagePage')
        else:
            messagebox.showerror('Error','Invalid credentials')

class StaffManagePage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text='Staff Management', font=('Helvetica',16)).pack(pady=8)
        ttk.Button(self, text='Back', command=lambda: controller.show_frame('StartPage')).pack()
        ttk.Button(self, text='Logout', command=lambda: controller.logout()).pack()

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

class CustomerAccountPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text='Customer Account', font=('Helvetica',16)).pack(pady=10)
        self.lbl_user = ttk.Label(self)
        self.lbl_user.pack()
        self.lbl_points = ttk.Label(self)
        self.lbl_points.pack()
        self.lbl_card = ttk.Label(self)
        self.lbl_card.pack(pady=6)
        ttk.Button(self, text='Add / Update Bank Card', command=self.add_card).pack(pady=4)
        ttk.Button(self, text='Go Shopping', command=lambda: controller.show_frame('ShoppingPage')).pack(pady=4)
        ttk.Button(self, text='Logout', command=lambda: controller.logout()).pack(pady=4)
        self.bind('<<ShowFrame>>', self.refresh)

    def refresh(self, event=None):
        u = self.controller.user
        if not u:
            return
        self.lbl_user.config(text=f'Username: {u["username"]}')
        pts = self.controller.query('SELECT loyalty_points, card_number FROM users WHERE id=?', (u['id'],), fetch=True)[0]
        self.lbl_points.config(text=f'Loyalty Points: {pts[0]}')
        self.lbl_card.config(text=f'Card: {pts[1] or "No card added"}')
        self.controller.user['card_number'] = pts[1]

    def add_card(self):
        card = simpledialog.askstring('Bank Card','Enter card number (mock)')
        if not card:
            return
        self.controller.query('UPDATE users SET card_number=? WHERE id=?',(card,self.controller.user['id']))
        messagebox.showinfo('Saved','Card saved successfully')
        self.refresh()

class AdminReportsPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        ttk.Label(self, text='Admin Reports', font=('Helvetica',16)).pack(pady=8)
        ttk.Button(self, text='Back', command=lambda: controller.show_frame('StartPage')).pack()
        self.txt=tk.Text(self,height=20)
        self.txt.pack(fill='both',expand=True,padx=8,pady=8)
        self.bind('<<ShowFrame>>', lambda e: self.refresh(controller))

    def refresh(self,controller):
        total=controller.query('SELECT SUM(total) FROM orders',fetch=True)[0][0]
        total=total or 0
        self.txt.delete('1.0','end')
        self.txt.insert('end',f'Total Sales: ${round(total,2)}\n')



# --- Run ---
if __name__=='__main__':
    conn = init_db()
    app = ShopApp(conn)
    app.mainloop()
