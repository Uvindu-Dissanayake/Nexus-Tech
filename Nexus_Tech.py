import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
import hashlib

class NexusTechSystem:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'jyGYdt8adnoa8w6r9q0phdisy-(fgix',
            'database': 'nexus_tech'
        }
        self.current_user = None
        self.user_role = None
        self.LOW_STOCK_THRESHOLD = 10
        
    def get_connection(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            messagebox.showerror("Database Error", f"Error connecting to database: {e}")
            return None
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def check_low_stock(self):
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT product_name, product_number FROM Product_Details WHERE product_number < %s", 
                          (self.LOW_STOCK_THRESHOLD,))
            low_stock_items = cursor.fetchall()
            conn.close()
            
            if low_stock_items:
                alert = "LOW STOCK ALERT:\n\n"
                for item in low_stock_items:
                    alert += f"{item[0]}: {item[1]} units remaining\n"
                messagebox.showwarning("Low Stock Notification", alert)
    
    def login(self, username, password, role):
        # Hardcoded credentials for testing (no database required)
        if role == "Staff" and username == "Staff" and password == "staff123":
            self.current_user = "Staff"
            self.user_role = role
            self.check_low_stock()
            return True
        elif role == "Admin" and username == "Admin123" and password == "admin123":
            self.current_user = "Admin123"
            self.user_role = role
            self.check_low_stock()
            return True
        
        # Database authentication (if hardcoded login fails)
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            hashed_pwd = self.hash_password(password)
            
            if role == "Staff":
                cursor.execute("SELECT staff_id, staff_name FROM Staff_Details WHERE staff_name = %s AND staff_password = %s",
                              (username, hashed_pwd))
            else:  # Admin
                cursor.execute("SELECT staff_id, staff_name FROM Staff_Details WHERE staff_name = %s AND staff_password = %s AND staff_id = 1",
                              (username, hashed_pwd))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                self.current_user = result[1]
                self.user_role = role
                self.check_low_stock()
                return True
        except:
            pass
        
        return False

class AdminWindow:
    def __init__(self, system):
        self.system = system
        self.root = tk.Tk()
        self.root.title("Nexus Tech - Admin Dashboard")
        self.root.geometry("1200x700")
        self.root.configure(bg='#ecf0f1')
        
        # Header
        header = tk.Frame(self.root, bg='#2c3e50', height=60)
        header.pack(fill='x')
        tk.Label(header, text=f"Admin: {system.current_user}", font=('Arial', 16, 'bold'),
                bg='#2c3e50', fg='#ecf0f1').pack(side='left', padx=20, pady=15)
        tk.Button(header, text="Logout", command=self.logout, bg='#e74c3c', fg='white').pack(side='right', padx=20)
        
        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tabs
        self.create_categories_tab()
        self.create_products_tab()
        self.create_customers_tab()
        self.create_reports_tab()
        self.create_customer_history_tab()
        
        self.root.mainloop()
    
    def create_categories_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Manage Categories')
        
        # Category Form
        form_frame = tk.LabelFrame(tab, text="Category Management", bg='#ecf0f1', padx=20, pady=20)
        form_frame.pack(fill='x', padx=10, pady=20)
        
        tk.Label(form_frame, text="Category Name:", bg='#ecf0f1', font=('Arial', 11)).grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.category_name = tk.Entry(form_frame, width=40, font=('Arial', 11))
        self.category_name.grid(row=0, column=1, padx=10, pady=10)
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg='#ecf0f1')
        btn_frame.grid(row=1, column=0, columnspan=2, pady=15)
        
        tk.Button(btn_frame, text="Add Category", command=self.add_category, 
                 bg='#27ae60', fg='white', width=15, font=('Arial', 10)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Update Category", command=self.update_category, 
                 bg='#f39c12', fg='white', width=15, font=('Arial', 10)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Delete Category", command=self.delete_category, 
                 bg='#e74c3c', fg='white', width=15, font=('Arial', 10)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_category_form, 
                 bg='#95a5a6', fg='white', width=15, font=('Arial', 10)).pack(side='left', padx=5)
        
        # Categories List
        list_frame = tk.LabelFrame(tab, text="Existing Categories", bg='#ecf0f1', padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.categories_tree = ttk.Treeview(list_frame, columns=('ID', 'Category Name'),
                                           show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.categories_tree.yview)
        
        self.categories_tree.heading('ID', text='ID')
        self.categories_tree.heading('Category Name', text='Category Name')
        
        self.categories_tree.column('ID', width=100)
        self.categories_tree.column('Category Name', width=400)
        
        self.categories_tree.pack(fill='both', expand=True)
        self.categories_tree.bind('<ButtonRelease-1>', self.on_category_select)
        
        self.refresh_categories()
    
    def refresh_categories(self):
        self.categories_tree.delete(*self.categories_tree.get_children())
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT category_id, category_name FROM Product_Category ORDER BY category_name")
                for row in cursor.fetchall():
                    self.categories_tree.insert('', 'end', values=row)
                conn.close()
            except:
                messagebox.showwarning("Database", "Database not available. Categories will be stored when database is connected.")
                conn.close()
    
    def on_category_select(self, event):
        selected = self.categories_tree.selection()
        if selected:
            values = self.categories_tree.item(selected[0])['values']
            self.category_name.delete(0, 'end')
            self.category_name.insert(0, values[1])
    
    def add_category(self):
        name = self.category_name.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Please enter a category name")
            return
        
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Product_Category (category_name) VALUES (%s)", (name,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Category added successfully")
                self.clear_category_form()
                self.refresh_categories()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add category: {str(e)}")
                conn.close()
        else:
            messagebox.showerror("Database Error", "Cannot add category without database connection")
    
    def update_category(self):
        selected = self.categories_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a category to update")
            return
        
        category_id = self.categories_tree.item(selected[0])['values'][0]
        name = self.category_name.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Please enter a category name")
            return
        
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE Product_Category SET category_name=%s WHERE category_id=%s", 
                             (name, category_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Category updated successfully")
                self.clear_category_form()
                self.refresh_categories()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update category: {str(e)}")
                conn.close()
        else:
            messagebox.showerror("Database Error", "Cannot update category without database connection")
    
    def delete_category(self):
        selected = self.categories_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a category to delete")
            return
        
        if messagebox.askyesno("Confirm", "Delete this category? This may affect products using this category."):
            category_id = self.categories_tree.item(selected[0])['values'][0]
            conn = self.system.get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Check if any products use this category
                    cursor.execute("SELECT COUNT(*) FROM Product_Details WHERE category_id=%s", (category_id,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        if not messagebox.askyesno("Warning", f"{count} product(s) use this category. Delete anyway?"):
                            conn.close()
                            return
                    
                    cursor.execute("DELETE FROM Product_Category WHERE category_id=%s", (category_id,))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Category deleted successfully")
                    self.clear_category_form()
                    self.refresh_categories()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete category: {str(e)}")
                    conn.close()
            else:
                messagebox.showerror("Database Error", "Cannot delete category without database connection")
    
    def clear_category_form(self):
        self.category_name.delete(0, 'end')
    
    def create_products_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Manage Products')
        
        # Product Form
        form_frame = tk.LabelFrame(tab, text="Product Information", bg='#ecf0f1', padx=10, pady=10)
        form_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(form_frame, text="Product Name:", bg='#ecf0f1').grid(row=0, column=0, padx=5, pady=5)
        self.prod_name = tk.Entry(form_frame, width=30)
        self.prod_name.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Category:", bg='#ecf0f1').grid(row=0, column=2, padx=5, pady=5)
        self.prod_category = ttk.Combobox(form_frame, width=28, state='readonly')
        self.prod_category.grid(row=0, column=3, padx=5, pady=5)
        self.load_categories()
        
        tk.Label(form_frame, text="Price:", bg='#ecf0f1').grid(row=1, column=0, padx=5, pady=5)
        self.prod_price = tk.Entry(form_frame, width=30)
        self.prod_price.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Quantity:", bg='#ecf0f1').grid(row=1, column=2, padx=5, pady=5)
        self.prod_quantity = tk.Entry(form_frame, width=30)
        self.prod_quantity.grid(row=1, column=3, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg='#ecf0f1')
        btn_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        tk.Button(btn_frame, text="Add Product", command=self.add_product, bg='#27ae60', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Update Product", command=self.update_product, bg='#f39c12', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Delete Product", command=self.delete_product, bg='#e74c3c', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_product_form, bg='#95a5a6', fg='white', width=15).pack(side='left', padx=5)
        
        # Products List
        list_frame = tk.Frame(tab, bg='#ecf0f1')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.products_tree = ttk.Treeview(list_frame, columns=('ID', 'Name', 'Category', 'Price', 'Quantity'),
                                         show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.products_tree.yview)
        
        self.products_tree.heading('ID', text='ID')
        self.products_tree.heading('Name', text='Product Name')
        self.products_tree.heading('Category', text='Category')
        self.products_tree.heading('Price', text='Price')
        self.products_tree.heading('Quantity', text='Quantity')
        
        self.products_tree.column('ID', width=50)
        self.products_tree.column('Name', width=250)
        self.products_tree.column('Category', width=150)
        self.products_tree.column('Price', width=100)
        self.products_tree.column('Quantity', width=100)
        
        self.products_tree.pack(fill='both', expand=True)
        self.products_tree.bind('<ButtonRelease-1>', self.on_product_select)
        
        self.refresh_products()
    
    def create_customers_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Manage Customers')
        
        # Customer Form
        form_frame = tk.LabelFrame(tab, text="Customer Information", bg='#ecf0f1', padx=10, pady=10)
        form_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(form_frame, text="Name:", bg='#ecf0f1').grid(row=0, column=0, padx=5, pady=5)
        self.cust_name = tk.Entry(form_frame, width=30)
        self.cust_name.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Contact:", bg='#ecf0f1').grid(row=0, column=2, padx=5, pady=5)
        self.cust_contact = tk.Entry(form_frame, width=30)
        self.cust_contact.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Label(form_frame, text="Email:", bg='#ecf0f1').grid(row=1, column=0, padx=5, pady=5)
        self.cust_email = tk.Entry(form_frame, width=30)
        self.cust_email.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Type:", bg='#ecf0f1').grid(row=1, column=2, padx=5, pady=5)
        self.cust_type = ttk.Combobox(form_frame, values=['Basic', 'Premium', 'Student'], width=28, state='readonly')
        self.cust_type.grid(row=1, column=3, padx=5, pady=5)
        self.cust_type.set('Basic')
        
        tk.Label(form_frame, text="Loyalty Points:", bg='#ecf0f1').grid(row=2, column=0, padx=5, pady=5)
        self.cust_points = tk.Entry(form_frame, width=30)
        self.cust_points.insert(0, '0')
        self.cust_points.grid(row=2, column=1, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg='#ecf0f1')
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10)
        
        tk.Button(btn_frame, text="Add Customer", command=self.add_customer, bg='#27ae60', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Update Customer", command=self.update_customer, bg='#f39c12', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Delete Customer", command=self.delete_customer, bg='#e74c3c', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_customer_form, bg='#95a5a6', fg='white', width=15).pack(side='left', padx=5)
        
        # Customers List
        list_frame = tk.Frame(tab, bg='#ecf0f1')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.customers_tree = ttk.Treeview(list_frame, columns=('ID', 'Name', 'Contact', 'Email', 'Type', 'Points'),
                                          show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.customers_tree.yview)
        
        self.customers_tree.heading('ID', text='ID')
        self.customers_tree.heading('Name', text='Name')
        self.customers_tree.heading('Contact', text='Contact')
        self.customers_tree.heading('Email', text='Email')
        self.customers_tree.heading('Type', text='Type')
        self.customers_tree.heading('Points', text='Loyalty Points')
        
        self.customers_tree.column('ID', width=50)
        self.customers_tree.column('Name', width=150)
        self.customers_tree.column('Contact', width=120)
        self.customers_tree.column('Email', width=200)
        self.customers_tree.column('Type', width=100)
        self.customers_tree.column('Points', width=100)
        
        self.customers_tree.pack(fill='both', expand=True)
        self.customers_tree.bind('<ButtonRelease-1>', self.on_customer_select)
        
        self.refresh_customers()
    
    def load_categories(self):
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT category_name FROM Product_Category")
                categories = [row[0] for row in cursor.fetchall()]
                self.prod_category['values'] = categories
                conn.close()
            except:
                conn.close()
    
    def refresh_products(self):
        self.products_tree.delete(*self.products_tree.get_children())
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.product_id, p.product_name, c.category_name, p.product_price, p.product_number
                    FROM Product_Details p
                    JOIN Product_Category c ON p.category_id = c.category_id
                """)
                for row in cursor.fetchall():
                    self.products_tree.insert('', 'end', values=row)
                conn.close()
            except:
                conn.close()
    
    def refresh_customers(self):
        self.customers_tree.delete(*self.customers_tree.get_children())
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM Customer_Details")
                for row in cursor.fetchall():
                    self.customers_tree.insert('', 'end', values=row)
                conn.close()
            except:
                conn.close()
    
    def on_product_select(self, event):
        selected = self.products_tree.selection()
        if selected:
            values = self.products_tree.item(selected[0])['values']
            self.prod_name.delete(0, 'end')
            self.prod_name.insert(0, values[1])
            self.prod_category.set(values[2])
            self.prod_price.delete(0, 'end')
            self.prod_price.insert(0, values[3])
            self.prod_quantity.delete(0, 'end')
            self.prod_quantity.insert(0, values[4])
    
    def on_customer_select(self, event):
        selected = self.customers_tree.selection()
        if selected:
            values = self.customers_tree.item(selected[0])['values']
            self.cust_name.delete(0, 'end')
            self.cust_name.insert(0, values[1])
            self.cust_contact.delete(0, 'end')
            self.cust_contact.insert(0, values[2])
            self.cust_email.delete(0, 'end')
            self.cust_email.insert(0, values[3])
            self.cust_type.set(values[4])
            self.cust_points.delete(0, 'end')
            self.cust_points.insert(0, values[5])
    
    def add_product(self):
        name = self.prod_name.get()
        category = self.prod_category.get()
        price = self.prod_price.get()
        quantity = self.prod_quantity.get()
        
        if not all([name, category, price, quantity]):
            messagebox.showerror("Error", "Please fill all fields")
            return
        
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT category_id FROM Product_Category WHERE category_name = %s", (category,))
                result = cursor.fetchone()
                if not result:
                    messagebox.showerror("Error", "Invalid category selected")
                    conn.close()
                    return
                cat_id = result[0]
                
                cursor.execute("""
                    INSERT INTO Product_Details (product_name, category_id, product_price, product_number)
                    VALUES (%s, %s, %s, %s)
                """, (name, cat_id, float(price), int(quantity)))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Product added successfully")
                self.clear_product_form()
                self.refresh_products()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add product: {str(e)}")
                conn.close()
        else:
            messagebox.showerror("Database Error", "Cannot add product without database connection")
    
    def update_product(self):
        selected = self.products_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a product")
            return
        
        product_id = self.products_tree.item(selected[0])['values'][0]
        name = self.prod_name.get()
        category = self.prod_category.get()
        price = self.prod_price.get()
        quantity = self.prod_quantity.get()
        
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT category_id FROM Product_Category WHERE category_name = %s", (category,))
                cat_id = cursor.fetchone()[0]
                
                cursor.execute("""
                    UPDATE Product_Details 
                    SET product_name=%s, category_id=%s, product_price=%s, product_number=%s
                    WHERE product_id=%s
                """, (name, cat_id, float(price), int(quantity), product_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Product updated successfully")
                self.clear_product_form()
                self.refresh_products()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update product: {str(e)}")
                conn.close()
        else:
            messagebox.showerror("Database Error", "Cannot update product without database connection")
    
    def delete_product(self):
        selected = self.products_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a product")
            return
        
        if messagebox.askyesno("Confirm", "Delete this product?"):
            product_id = self.products_tree.item(selected[0])['values'][0]
            conn = self.system.get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM Product_Details WHERE product_id=%s", (product_id,))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Product deleted successfully")
                    self.clear_product_form()
                    self.refresh_products()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete product: {str(e)}")
                    conn.close()
            else:
                messagebox.showerror("Database Error", "Cannot delete product without database connection")
    
    def clear_product_form(self):
        self.prod_name.delete(0, 'end')
        self.prod_category.set('')
        self.prod_price.delete(0, 'end')
        self.prod_quantity.delete(0, 'end')
    
    def add_customer(self):
        name = self.cust_name.get()
        contact = self.cust_contact.get()
        email = self.cust_email.get()
        ctype = self.cust_type.get()
        points = self.cust_points.get()
        
        if not all([name, contact, email, ctype]):
            messagebox.showerror("Error", "Please fill all required fields")
            return
        
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Customer_Details (customer_name, customer_contact, customer_email, customer_type, loyalty_points)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, contact, email, ctype, int(points)))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Customer added successfully")
                self.clear_customer_form()
                self.refresh_customers()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add customer: {str(e)}")
                conn.close()
        else:
            messagebox.showerror("Database Error", "Cannot add customer without database connection")
    
    def update_customer(self):
        selected = self.customers_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a customer")
            return
        
        customer_id = self.customers_tree.item(selected[0])['values'][0]
        name = self.cust_name.get()
        contact = self.cust_contact.get()
        email = self.cust_email.get()
        ctype = self.cust_type.get()
        points = self.cust_points.get()
        
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE Customer_Details 
                    SET customer_name=%s, customer_contact=%s, customer_email=%s, customer_type=%s, loyalty_points=%s
                    WHERE customer_id=%s
                """, (name, contact, email, ctype, int(points), customer_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Customer updated successfully")
                self.clear_customer_form()
                self.refresh_customers()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update customer: {str(e)}")
                conn.close()
        else:
            messagebox.showerror("Database Error", "Cannot update customer without database connection")
    
    def delete_customer(self):
        selected = self.customers_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a customer")
            return
        
        if messagebox.askyesno("Confirm", "Delete this customer?"):
            customer_id = self.customers_tree.item(selected[0])['values'][0]
            conn = self.system.get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM Customer_Details WHERE customer_id=%s", (customer_id,))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Customer deleted successfully")
                    self.clear_customer_form()
                    self.refresh_customers()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete customer: {str(e)}")
                    conn.close()
            else:
                messagebox.showerror("Database Error", "Cannot delete customer without database connection")
    
    def clear_customer_form(self):
        self.cust_name.delete(0, 'end')
        self.cust_contact.delete(0, 'end')
        self.cust_email.delete(0, 'end')
        self.cust_type.set('Basic')
        self.cust_points.delete(0, 'end')
        self.cust_points.insert(0, '0')
    
    def create_reports_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Reports')
        
        # Report buttons
        btn_frame = tk.Frame(tab, bg='#ecf0f1')
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Sales Summary", command=self.show_sales_summary, 
                 bg='#3498db', fg='white', width=20, height=2).pack(side='left', padx=10)
        tk.Button(btn_frame, text="Low Stock Report", command=self.show_low_stock, 
                 bg='#e74c3c', fg='white', width=20, height=2).pack(side='left', padx=10)
        tk.Button(btn_frame, text="Customer Report", command=self.show_customer_report, 
                 bg='#9b59b6', fg='white', width=20, height=2).pack(side='left', padx=10)
        
        # Report display area
        report_frame = tk.LabelFrame(tab, text="Report Details", bg='#ecf0f1', padx=10, pady=10)
        report_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(report_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.report_tree = ttk.Treeview(report_frame, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.report_tree.yview)
        self.report_tree.pack(fill='both', expand=True)
    
    def create_customer_history_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Customer History')
        
        # Customer selection
        top_frame = tk.Frame(tab, bg='#ecf0f1')
        top_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(top_frame, text="Select Customer:", bg='#ecf0f1', font=('Arial', 12)).pack(side='left', padx=5)
        self.history_customer = ttk.Combobox(top_frame, width=40, state='readonly')
        self.history_customer.pack(side='left', padx=5)
        self.load_customers_for_history()
        
        tk.Button(top_frame, text="View History", command=self.view_customer_history,
                 bg='#27ae60', fg='white').pack(side='left', padx=5)
        
        # Customer info display
        info_frame = tk.LabelFrame(tab, text="Customer Information", bg='#ecf0f1', padx=10, pady=10)
        info_frame.pack(fill='x', padx=10, pady=10)
        
        self.customer_info = tk.Text(info_frame, height=5, bg='white')
        self.customer_info.pack(fill='x')
        
        # History display
        history_frame = tk.LabelFrame(tab, text="Purchase History", bg='#ecf0f1', padx=10, pady=10)
        history_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.history_text = tk.Text(history_frame, bg='white')
        self.history_text.pack(fill='both', expand=True)
    
    def show_sales_summary(self):
        self.report_tree.delete(*self.report_tree.get_children())
        self.report_tree['columns'] = ('Product', 'Category', 'Price', 'Stock')
        self.report_tree['show'] = 'headings'
        
        self.report_tree.heading('Product', text='Product Name')
        self.report_tree.heading('Category', text='Category')
        self.report_tree.heading('Price', text='Price')
        self.report_tree.heading('Stock', text='Current Stock')
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.product_name, c.category_name, p.product_price, p.product_number
                FROM Product_Details p
                JOIN Product_Category c ON p.category_id = c.category_id
                ORDER BY p.product_name
            """)
            for row in cursor.fetchall():
                self.report_tree.insert('', 'end', values=row)
            conn.close()
    
    def show_low_stock(self):
        self.report_tree.delete(*self.report_tree.get_children())
        self.report_tree['columns'] = ('Product', 'Category', 'Stock', 'Status')
        self.report_tree['show'] = 'headings'
        
        self.report_tree.heading('Product', text='Product Name')
        self.report_tree.heading('Category', text='Category')
        self.report_tree.heading('Stock', text='Stock Level')
        self.report_tree.heading('Status', text='Status')
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.product_name, c.category_name, p.product_number,
                CASE 
                    WHEN p.product_number = 0 THEN 'OUT OF STOCK'
                    WHEN p.product_number < 10 THEN 'LOW STOCK'
                    ELSE 'REORDER SOON'
                END as status
                FROM Product_Details p
                JOIN Product_Category c ON p.category_id = c.category_id
                WHERE p.product_number < 20
                ORDER BY p.product_number
            """)
            for row in cursor.fetchall():
                self.report_tree.insert('', 'end', values=row)
            conn.close()
    
    def show_customer_report(self):
        self.report_tree.delete(*self.report_tree.get_children())
        self.report_tree['columns'] = ('Name', 'Type', 'Points', 'Contact', 'Email')
        self.report_tree['show'] = 'headings'
        
        self.report_tree.heading('Name', text='Customer Name')
        self.report_tree.heading('Type', text='Type')
        self.report_tree.heading('Points', text='Loyalty Points')
        self.report_tree.heading('Contact', text='Contact')
        self.report_tree.heading('Email', text='Email')
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT customer_name, customer_type, loyalty_points, customer_contact, customer_email
                FROM Customer_Details
                ORDER BY loyalty_points DESC
            """)
            for row in cursor.fetchall():
                self.report_tree.insert('', 'end', values=row)
            conn.close()
    
    def load_customers_for_history(self):
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id, customer_name FROM Customer_Details")
            customers = [f"{row[0]} - {row[1]}" for row in cursor.fetchall()]
            self.history_customer['values'] = customers
            conn.close()
    
    def view_customer_history(self):
        customer = self.history_customer.get()
        if not customer:
            messagebox.showerror("Error", "Please select a customer")
            return
        
        customer_id = int(customer.split(' - ')[0])
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Customer_Details WHERE customer_id=%s", (customer_id,))
            cust_data = cursor.fetchone()
            conn.close()
            
            if cust_data:
                self.customer_info.delete('1.0', 'end')
                info = f"Customer ID: {cust_data[0]}\n"
                info += f"Name: {cust_data[1]}\n"
                info += f"Contact: {cust_data[2]}\n"
                info += f"Email: {cust_data[3]}\n"
                info += f"Type: {cust_data[4]}\n"
                info += f"Loyalty Points: {cust_data[5]}\n"
                self.customer_info.insert('1.0', info)
                
                self.history_text.delete('1.0', 'end')
                self.history_text.insert('1.0', "Purchase history functionality can be extended by creating a Transactions table.\nThis would store all checkout records with timestamps and product details.")
    
    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.root.destroy()
            system = NexusTechSystem()
            login_window = LoginWindow(system)
            login_window.root.mainloop()

class LoginWindow:
    def __init__(self, system):
        self.system = system
        self.root = tk.Tk()
        self.root.title("Nexus Tech - Login")
        self.root.geometry("400x300")
        self.root.configure(bg='#2c3e50')
        
        # Title
        title = tk.Label(self.root, text="NEXUS TECH", font=('Arial', 24, 'bold'), 
                        bg='#2c3e50', fg='#ecf0f1')
        title.pack(pady=20)
        
        # Login Frame
        frame = tk.Frame(self.root, bg='#34495e', padx=20, pady=20)
        frame.pack(pady=20)
        
        tk.Label(frame, text="Username:", bg='#34495e', fg='#ecf0f1').grid(row=0, column=0, pady=10, sticky='w')
        self.username_entry = tk.Entry(frame, width=25)
        self.username_entry.grid(row=0, column=1, pady=10)
        
        tk.Label(frame, text="Password:", bg='#34495e', fg='#ecf0f1').grid(row=1, column=0, pady=10, sticky='w')
        self.password_entry = tk.Entry(frame, width=25, show='*')
        self.password_entry.grid(row=1, column=1, pady=10)
        
        tk.Label(frame, text="Role:", bg='#34495e', fg='#ecf0f1').grid(row=2, column=0, pady=10, sticky='w')
        self.role_var = tk.StringVar(value="Staff")
        role_combo = ttk.Combobox(frame, textvariable=self.role_var, values=["Staff", "Admin"], 
                                  state='readonly', width=23)
        role_combo.grid(row=2, column=1, pady=10)
        
        login_btn = tk.Button(frame, text="Login", command=self.login, 
                             bg='#27ae60', fg='white', width=20)
        login_btn.grid(row=3, column=0, columnspan=2, pady=20)
        
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        role = self.role_var.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill all fields")
            return
        
        if self.system.login(username, password, role):
            self.root.destroy()
            print(f"Login successful! Role: {role}")  # Debug print
            if role == "Admin":
                print("Opening Admin Window")  # Debug print
                admin_win = AdminWindow(self.system)
            else:
                print("Opening Staff Window")  # Debug print
                staff_win = StaffWindow(self.system)
        else:
            messagebox.showerror("Error", "Invalid credentials")

class StaffWindow:
    def __init__(self, system):
        self.system = system
        self.root = tk.Tk()
        self.root.title("Nexus Tech - Staff Dashboard")
        self.root.geometry("1200x700")
        self.root.configure(bg='#ecf0f1')
        
        # Header
        header = tk.Frame(self.root, bg='#2c3e50', height=60)
        header.pack(fill='x')
        tk.Label(header, text=f"Welcome, {system.current_user}", font=('Arial', 16, 'bold'),
                bg='#2c3e50', fg='#ecf0f1').pack(side='left', padx=20, pady=15)
        tk.Button(header, text="Logout", command=self.logout, bg='#e74c3c', fg='white').pack(side='right', padx=20)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tabs
        self.create_products_tab()
        self.create_customers_tab()
        self.create_checkout_tab()
        
        self.root.mainloop()
    
    def create_products_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Products')
        
        # Product Form
        form_frame = tk.LabelFrame(tab, text="Product Information", bg='#ecf0f1', padx=10, pady=10)
        form_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(form_frame, text="Product Name:", bg='#ecf0f1').grid(row=0, column=0, padx=5, pady=5)
        self.prod_name = tk.Entry(form_frame, width=30)
        self.prod_name.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Category:", bg='#ecf0f1').grid(row=0, column=2, padx=5, pady=5)
        self.prod_category = ttk.Combobox(form_frame, width=28, state='readonly')
        self.prod_category.grid(row=0, column=3, padx=5, pady=5)
        self.load_categories()
        
        tk.Label(form_frame, text="Price:", bg='#ecf0f1').grid(row=1, column=0, padx=5, pady=5)
        self.prod_price = tk.Entry(form_frame, width=30)
        self.prod_price.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Quantity:", bg='#ecf0f1').grid(row=1, column=2, padx=5, pady=5)
        self.prod_quantity = tk.Entry(form_frame, width=30)
        self.prod_quantity.grid(row=1, column=3, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg='#ecf0f1')
        btn_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        tk.Button(btn_frame, text="Add Product", command=self.add_product, bg='#27ae60', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Update Product", command=self.update_product, bg='#f39c12', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Delete Product", command=self.delete_product, bg='#e74c3c', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_product_form, bg='#95a5a6', fg='white', width=15).pack(side='left', padx=5)
        
        # Products List
        list_frame = tk.Frame(tab, bg='#ecf0f1')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.products_tree = ttk.Treeview(list_frame, columns=('ID', 'Name', 'Category', 'Price', 'Quantity'),
                                         show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.products_tree.yview)
        
        self.products_tree.heading('ID', text='ID')
        self.products_tree.heading('Name', text='Product Name')
        self.products_tree.heading('Category', text='Category')
        self.products_tree.heading('Price', text='Price')
        self.products_tree.heading('Quantity', text='Quantity')
        
        self.products_tree.column('ID', width=50)
        self.products_tree.column('Name', width=250)
        self.products_tree.column('Category', width=150)
        self.products_tree.column('Price', width=100)
        self.products_tree.column('Quantity', width=100)
        
        self.products_tree.pack(fill='both', expand=True)
        self.products_tree.bind('<ButtonRelease-1>', self.on_product_select)
        
        self.refresh_products()
    
    def create_customers_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Customers')
        
        # Customer Form
        form_frame = tk.LabelFrame(tab, text="Customer Information", bg='#ecf0f1', padx=10, pady=10)
        form_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(form_frame, text="Name:", bg='#ecf0f1').grid(row=0, column=0, padx=5, pady=5)
        self.cust_name = tk.Entry(form_frame, width=30)
        self.cust_name.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Contact:", bg='#ecf0f1').grid(row=0, column=2, padx=5, pady=5)
        self.cust_contact = tk.Entry(form_frame, width=30)
        self.cust_contact.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Label(form_frame, text="Email:", bg='#ecf0f1').grid(row=1, column=0, padx=5, pady=5)
        self.cust_email = tk.Entry(form_frame, width=30)
        self.cust_email.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(form_frame, text="Type:", bg='#ecf0f1').grid(row=1, column=2, padx=5, pady=5)
        self.cust_type = ttk.Combobox(form_frame, values=['Basic', 'Premium', 'Student'], width=28, state='readonly')
        self.cust_type.grid(row=1, column=3, padx=5, pady=5)
        self.cust_type.set('Basic')
        
        tk.Label(form_frame, text="Loyalty Points:", bg='#ecf0f1').grid(row=2, column=0, padx=5, pady=5)
        self.cust_points = tk.Entry(form_frame, width=30)
        self.cust_points.insert(0, '0')
        self.cust_points.grid(row=2, column=1, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg='#ecf0f1')
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10)
        
        tk.Button(btn_frame, text="Add Customer", command=self.add_customer, bg='#27ae60', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Update Customer", command=self.update_customer, bg='#f39c12', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Delete Customer", command=self.delete_customer, bg='#e74c3c', fg='white', width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_customer_form, bg='#95a5a6', fg='white', width=15).pack(side='left', padx=5)
        
        # Customers List
        list_frame = tk.Frame(tab, bg='#ecf0f1')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.customers_tree = ttk.Treeview(list_frame, columns=('ID', 'Name', 'Contact', 'Email', 'Type', 'Points'),
                                          show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.customers_tree.yview)
        
        self.customers_tree.heading('ID', text='ID')
        self.customers_tree.heading('Name', text='Name')
        self.customers_tree.heading('Contact', text='Contact')
        self.customers_tree.heading('Email', text='Email')
        self.customers_tree.heading('Type', text='Type')
        self.customers_tree.heading('Points', text='Loyalty Points')
        
        self.customers_tree.column('ID', width=50)
        self.customers_tree.column('Name', width=150)
        self.customers_tree.column('Contact', width=120)
        self.customers_tree.column('Email', width=200)
        self.customers_tree.column('Type', width=100)
        self.customers_tree.column('Points', width=100)
        
        self.customers_tree.pack(fill='both', expand=True)
        self.customers_tree.bind('<ButtonRelease-1>', self.on_customer_select)
        
        self.refresh_customers()
    
    def create_checkout_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Checkout')
        
        # Customer Selection
        top_frame = tk.Frame(tab, bg='#ecf0f1')
        top_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(top_frame, text="Select Customer:", bg='#ecf0f1', font=('Arial', 12)).pack(side='left', padx=5)
        self.checkout_customer = ttk.Combobox(top_frame, width=40, state='readonly')
        self.checkout_customer.pack(side='left', padx=5)
        self.load_customers_for_checkout()
        
        # Product Selection
        product_frame = tk.LabelFrame(tab, text="Add Products", bg='#ecf0f1', padx=10, pady=10)
        product_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(product_frame, text="Product:", bg='#ecf0f1').grid(row=0, column=0, padx=5, pady=5)
        self.checkout_product = ttk.Combobox(product_frame, width=35, state='readonly')
        self.checkout_product.grid(row=0, column=1, padx=5, pady=5)
        self.load_products_for_checkout()
        
        tk.Label(product_frame, text="Quantity:", bg='#ecf0f1').grid(row=0, column=2, padx=5, pady=5)
        self.checkout_quantity = tk.Entry(product_frame, width=10)
        self.checkout_quantity.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Button(product_frame, text="Add to Cart", command=self.add_to_cart, bg='#3498db', fg='white').grid(row=0, column=4, padx=5, pady=5)
        
        # Cart
        cart_frame = tk.LabelFrame(tab, text="Shopping Cart", bg='#ecf0f1', padx=10, pady=10)
        cart_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.cart_tree = ttk.Treeview(cart_frame, columns=('Product', 'Price', 'Quantity', 'Total'),
                                     show='headings', height=10)
        
        self.cart_tree.heading('Product', text='Product')
        self.cart_tree.heading('Price', text='Price')
        self.cart_tree.heading('Quantity', text='Quantity')
        self.cart_tree.heading('Total', text='Total')
        
        self.cart_tree.column('Product', width=300)
        self.cart_tree.column('Price', width=100)
        self.cart_tree.column('Quantity', width=100)
        self.cart_tree.column('Total', width=100)
        
        self.cart_tree.pack(fill='both', expand=True)
        
        tk.Button(cart_frame, text="Remove Selected", command=self.remove_from_cart, bg='#e74c3c', fg='white').pack(pady=5)
        
        # Total Frame
        total_frame = tk.Frame(tab, bg='#ecf0f1')
        total_frame.pack(fill='x', padx=10, pady=10)
        
        self.subtotal_label = tk.Label(total_frame, text="Subtotal: $0.00", bg='#ecf0f1', font=('Arial', 12))
        self.subtotal_label.pack()
        
        self.discount_label = tk.Label(total_frame, text="Discount: $0.00", bg='#ecf0f1', font=('Arial', 12))
        self.discount_label.pack()
        
        self.total_label = tk.Label(total_frame, text="Total: $0.00", bg='#ecf0f1', font=('Arial', 14, 'bold'))
        self.total_label.pack()
        
        tk.Button(total_frame, text="Complete Checkout", command=self.complete_checkout, 
                 bg='#27ae60', fg='white', font=('Arial', 12, 'bold'), padx=20, pady=10).pack(pady=10)
    
    def load_categories(self):
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category_name FROM Product_Category")
            categories = [row[0] for row in cursor.fetchall()]
            self.prod_category['values'] = categories
            conn.close()
    
    def refresh_products(self):
        self.products_tree.delete(*self.products_tree.get_children())
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.product_id, p.product_name, c.category_name, p.product_price, p.product_number
                FROM Product_Details p
                JOIN Product_Category c ON p.category_id = c.category_id
            """)
            for row in cursor.fetchall():
                self.products_tree.insert('', 'end', values=row)
            conn.close()
    
    def refresh_customers(self):
        self.customers_tree.delete(*self.customers_tree.get_children())
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Customer_Details")
            for row in cursor.fetchall():
                self.customers_tree.insert('', 'end', values=row)
            conn.close()
    
    def on_product_select(self, event):
        selected = self.products_tree.selection()
        if selected:
            values = self.products_tree.item(selected[0])['values']
            self.prod_name.delete(0, 'end')
            self.prod_name.insert(0, values[1])
            self.prod_category.set(values[2])
            self.prod_price.delete(0, 'end')
            self.prod_price.insert(0, values[3])
            self.prod_quantity.delete(0, 'end')
            self.prod_quantity.insert(0, values[4])
    
    def on_customer_select(self, event):
        selected = self.customers_tree.selection()
        if selected:
            values = self.customers_tree.item(selected[0])['values']
            self.cust_name.delete(0, 'end')
            self.cust_name.insert(0, values[1])
            self.cust_contact.delete(0, 'end')
            self.cust_contact.insert(0, values[2])
            self.cust_email.delete(0, 'end')
            self.cust_email.insert(0, values[3])
            self.cust_type.set(values[4])
            self.cust_points.delete(0, 'end')
            self.cust_points.insert(0, values[5])
    
    def add_product(self):
        name = self.prod_name.get()
        category = self.prod_category.get()
        price = self.prod_price.get()
        quantity = self.prod_quantity.get()
        
        if not all([name, category, price, quantity]):
            messagebox.showerror("Error", "Please fill all fields")
            return
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category_id FROM Product_Category WHERE category_name = %s", (category,))
            cat_id = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO Product_Details (product_name, category_id, product_price, product_number)
                VALUES (%s, %s, %s, %s)
            """, (name, cat_id, float(price), int(quantity)))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added successfully")
            self.clear_product_form()
            self.refresh_products()
    
    def update_product(self):
        selected = self.products_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a product")
            return
        
        product_id = self.products_tree.item(selected[0])['values'][0]
        name = self.prod_name.get()
        category = self.prod_category.get()
        price = self.prod_price.get()
        quantity = self.prod_quantity.get()
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category_id FROM Product_Category WHERE category_name = %s", (category,))
            cat_id = cursor.fetchone()[0]
            
            cursor.execute("""
                UPDATE Product_Details 
                SET product_name=%s, category_id=%s, product_price=%s, product_number=%s
                WHERE product_id=%s
            """, (name, cat_id, float(price), int(quantity), product_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product updated successfully")
            self.clear_product_form()
            self.refresh_products()
    
    def delete_product(self):
        selected = self.products_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a product")
            return
        
        if messagebox.askyesno("Confirm", "Delete this product?"):
            product_id = self.products_tree.item(selected[0])['values'][0]
            conn = self.system.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Product_Details WHERE product_id=%s", (product_id,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Product deleted successfully")
                self.clear_product_form()
                self.refresh_products()
    
    def clear_product_form(self):
        self.prod_name.delete(0, 'end')
        self.prod_category.set('')
        self.prod_price.delete(0, 'end')
        self.prod_quantity.delete(0, 'end')
    
    def add_customer(self):
        name = self.cust_name.get()
        contact = self.cust_contact.get()
        email = self.cust_email.get()
        ctype = self.cust_type.get()
        points = self.cust_points.get()
        
        if not all([name, contact, email, ctype]):
            messagebox.showerror("Error", "Please fill all required fields")
            return
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Customer_Details (customer_name, customer_contact, customer_email, customer_type, loyalty_points)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, contact, email, ctype, int(points)))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Customer added successfully")
            self.clear_customer_form()
            self.refresh_customers()
    
    def update_customer(self):
        selected = self.customers_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a customer")
            return
        
        customer_id = self.customers_tree.item(selected[0])['values'][0]
        name = self.cust_name.get()
        contact = self.cust_contact.get()
        email = self.cust_email.get()
        ctype = self.cust_type.get()
        points = self.cust_points.get()
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Customer_Details 
                SET customer_name=%s, customer_contact=%s, customer_email=%s, customer_type=%s, loyalty_points=%s
                WHERE customer_id=%s
            """, (name, contact, email, ctype, int(points), customer_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Customer updated successfully")
            self.clear_customer_form()
            self.refresh_customers()
    
    def delete_customer(self):
        selected = self.customers_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a customer")
            return
        
        if messagebox.askyesno("Confirm", "Delete this customer?"):
            customer_id = self.customers_tree.item(selected[0])['values'][0]
            conn = self.system.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Customer_Details WHERE customer_id=%s", (customer_id,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Customer deleted successfully")
                self.clear_customer_form()
                self.refresh_customers()
    
    def clear_customer_form(self):
        self.cust_name.delete(0, 'end')
        self.cust_contact.delete(0, 'end')
        self.cust_email.delete(0, 'end')
        self.cust_type.set('Basic')
        self.cust_points.delete(0, 'end')
        self.cust_points.insert(0, '0')
    
    def load_customers_for_checkout(self):
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id, customer_name FROM Customer_Details")
            customers = [f"{row[0]} - {row[1]}" for row in cursor.fetchall()]
            self.checkout_customer['values'] = customers
            conn.close()
    
    def load_products_for_checkout(self):
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT product_id, product_name, product_price FROM Product_Details WHERE product_number > 0")
            products = [f"{row[0]} - {row[1]} (${row[2]})" for row in cursor.fetchall()]
            self.checkout_product['values'] = products
            conn.close()
    
    def add_to_cart(self):
        product = self.checkout_product.get()
        quantity = self.checkout_quantity.get()
        
        if not product or not quantity:
            messagebox.showerror("Error", "Please select product and quantity")
            return
        
        try:
            quantity = int(quantity)
            product_id = int(product.split(' - ')[0])
            
            conn = self.system.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT product_name, product_price, product_number FROM Product_Details WHERE product_id=%s", (product_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    prod_name, price, stock = result
                    if quantity > stock:
                        messagebox.showerror("Error", f"Only {stock} units available")
                        return
                    
                    total = price * quantity
                    self.cart_tree.insert('', 'end', values=(prod_name, f"${price:.2f}", quantity, f"${total:.2f}"))
                    self.update_cart_totals()
                    self.checkout_quantity.delete(0, 'end')
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
    
    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if selected:
            self.cart_tree.delete(selected[0])
            self.update_cart_totals()
    
    def update_cart_totals(self):
        subtotal = 0
        for item in self.cart_tree.get_children():
            values = self.cart_tree.item(item)['values']
            subtotal += float(values[3].replace(', '))
        
        discount = 0
        customer = self.checkout_customer.get()
        if customer:
            customer_id = int(customer.split(' - ')[0])
            conn = self.system.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT customer_type, loyalty_points FROM Customer_Details WHERE customer_id=%s", (customer_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    cust_type, points = result
                    # Customer type discounts
                    if cust_type == 'Premium':
                        discount += subtotal * 0.15  # 15% discount
                    elif cust_type == 'Student':
                        discount += subtotal * 0.10  # 10% discount
                    
                    # Loyalty points discount (100 points = $10 discount)
                    discount += (points // 100) * 10
        
        total = subtotal - discount
        
        self.subtotal_label.config(text=f"Subtotal: ${subtotal:.2f}")
        self.discount_label.config(text=f"Discount: ${discount:.2f}")
        self.total_label.config(text=f"Total: ${total:.2f}")
    
    def complete_checkout(self):
        customer = self.checkout_customer.get()
        if not customer:
            messagebox.showerror("Error", "Please select a customer")
            return
        
        items = self.cart_tree.get_children()
        if not items:
            messagebox.showerror("Error", "Cart is empty")
            return
        
        customer_id = int(customer.split(' - ')[0])
        
        # Calculate totals
        subtotal = 0
        for item in items:
            values = self.cart_tree.item(item)['values']
            subtotal += float(values[3].replace(', '))
        
        # Update inventory and loyalty points
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            
            # Get customer info
            cursor.execute("SELECT customer_type, loyalty_points FROM Customer_Details WHERE customer_id=%s", (customer_id,))
            cust_type, current_points = cursor.fetchone()
            
            # Calculate discount
            discount = 0
            if cust_type == 'Premium':
                discount += subtotal * 0.15
            elif cust_type == 'Student':
                discount += subtotal * 0.10
            
            points_used = (current_points // 100) * 100
            discount += (points_used // 100) * 10
            
            total = subtotal - discount
            
            # Update inventory
            for item in items:
                values = self.cart_tree.item(item)['values']
                prod_name = values[0]
                quantity = values[2]
                
                cursor.execute("UPDATE Product_Details SET product_number = product_number - %s WHERE product_name=%s",
                             (quantity, prod_name))
            
            # Update loyalty points (earn 1 point per dollar spent, minus used points)
            new_points = current_points - points_used + int(total)
            cursor.execute("UPDATE Customer_Details SET loyalty_points=%s WHERE customer_id=%s",
                         (new_points, customer_id))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", f"Checkout completed!\nTotal: ${total:.2f}\nNew Loyalty Points: {new_points}")
            
            # Clear cart
            for item in items:
                self.cart_tree.delete(item)
            self.update_cart_totals()
            self.refresh_products()
            self.load_products_for_checkout()
    
    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.root.destroy()
            system = NexusTechSystem()
            login_window = LoginWindow(system)
            login_window.root.mainloop()

class AdminWindow:
    def __init__(self, system):
        self.system = system
        self.root = tk.Tk()
        self.root.title("Nexus Tech - Admin Dashboard")
        self.root.geometry("1200x700")
        self.root.configure(bg='#ecf0f1')
        
        # Header
        header = tk.Frame(self.root, bg='#2c3e50', height=60)
        header.pack(fill='x')
        tk.Label(header, text=f"Admin: {system.current_user}", font=('Arial', 16, 'bold'),
                bg='#2c3e50', fg='#ecf0f1').pack(side='left', padx=20, pady=15)
        tk.Button(header, text="Logout", command=self.logout, bg='#e74c3c', fg='white').pack(side='right', padx=20)
        
        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tabs
        self.create_categories_tab()
        self.create_reports_tab()
        self.create_customer_history_tab()
        
        self.root.mainloop()
    
    
    def create_categories_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Manage Categories')
        
        # Category Form
        form_frame = tk.LabelFrame(tab, text="Category Management", bg='#ecf0f1', padx=20, pady=20)
        form_frame.pack(fill='x', padx=10, pady=20)
        
        tk.Label(form_frame, text="Category Name:", bg='#ecf0f1', font=('Arial', 11)).grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.category_name = tk.Entry(form_frame, width=40, font=('Arial', 11))
        self.category_name.grid(row=0, column=1, padx=10, pady=10)
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg='#ecf0f1')
        btn_frame.grid(row=1, column=0, columnspan=2, pady=15)
        
        tk.Button(btn_frame, text="Add Category", command=self.add_category, 
                 bg='#27ae60', fg='white', width=15, font=('Arial', 10)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Update Category", command=self.update_category, 
                 bg='#f39c12', fg='white', width=15, font=('Arial', 10)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Delete Category", command=self.delete_category, 
                 bg='#e74c3c', fg='white', width=15, font=('Arial', 10)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_category_form, 
                 bg='#95a5a6', fg='white', width=15, font=('Arial', 10)).pack(side='left', padx=5)
        
        # Categories List
        list_frame = tk.LabelFrame(tab, text="Existing Categories", bg='#ecf0f1', padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.categories_tree = ttk.Treeview(list_frame, columns=('ID', 'Category Name'),
                                           show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.categories_tree.yview)
        
        self.categories_tree.heading('ID', text='ID')
        self.categories_tree.heading('Category Name', text='Category Name')
        
        self.categories_tree.column('ID', width=100)
        self.categories_tree.column('Category Name', width=400)
        
        self.categories_tree.pack(fill='both', expand=True)
        self.categories_tree.bind('<ButtonRelease-1>', self.on_category_select)
        
        self.refresh_categories()
    
    def refresh_categories(self):
        self.categories_tree.delete(*self.categories_tree.get_children())
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT category_id, category_name FROM Product_Category ORDER BY category_name")
                for row in cursor.fetchall():
                    self.categories_tree.insert('', 'end', values=row)
                conn.close()
            except:
                messagebox.showwarning("Database", "Database not available. Categories will be stored when database is connected.")
                conn.close()
    
    def on_category_select(self, event):
        selected = self.categories_tree.selection()
        if selected:
            values = self.categories_tree.item(selected[0])['values']
            self.category_name.delete(0, 'end')
            self.category_name.insert(0, values[1])
    
    def add_category(self):
        name = self.category_name.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Please enter a category name")
            return
        
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Product_Category (category_name) VALUES (%s)", (name,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Category added successfully")
                self.clear_category_form()
                self.refresh_categories()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add category: {str(e)}")
                conn.close()
        else:
            messagebox.showerror("Database Error", "Cannot add category without database connection")
    
    def update_category(self):
        selected = self.categories_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a category to update")
            return
        
        category_id = self.categories_tree.item(selected[0])['values'][0]
        name = self.category_name.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Please enter a category name")
            return
        
        conn = self.system.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE Product_Category SET category_name=%s WHERE category_id=%s", 
                             (name, category_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Category updated successfully")
                self.clear_category_form()
                self.refresh_categories()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update category: {str(e)}")
                conn.close()
        else:
            messagebox.showerror("Database Error", "Cannot update category without database connection")
    
    def delete_category(self):
        selected = self.categories_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a category to delete")
            return
        
        if messagebox.askyesno("Confirm", "Delete this category? This may affect products using this category."):
            category_id = self.categories_tree.item(selected[0])['values'][0]
            conn = self.system.get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Check if any products use this category
                    cursor.execute("SELECT COUNT(*) FROM Product_Details WHERE category_id=%s", (category_id,))
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        if not messagebox.askyesno("Warning", f"{count} product(s) use this category. Delete anyway?"):
                            conn.close()
                            return
                    
                    cursor.execute("DELETE FROM Product_Category WHERE category_id=%s", (category_id,))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Success", "Category deleted successfully")
                    self.clear_category_form()
                    self.refresh_categories()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete category: {str(e)}")
                    conn.close()
            else:
                messagebox.showerror("Database Error", "Cannot delete category without database connection")
    
    def clear_category_form(self):
        self.category_name.delete(0, 'end')
    
    def create_reports_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Reports')
        
        # Report buttons
        btn_frame = tk.Frame(tab, bg='#ecf0f1')
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Sales Summary", command=self.show_sales_summary, 
                 bg='#3498db', fg='white', width=20, height=2).pack(side='left', padx=10)
        tk.Button(btn_frame, text="Low Stock Report", command=self.show_low_stock, 
                 bg='#e74c3c', fg='white', width=20, height=2).pack(side='left', padx=10)
        tk.Button(btn_frame, text="Customer Report", command=self.show_customer_report, 
                 bg='#9b59b6', fg='white', width=20, height=2).pack(side='left', padx=10)
        
        # Report display area
        report_frame = tk.LabelFrame(tab, text="Report Details", bg='#ecf0f1', padx=10, pady=10)
        report_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(report_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.report_tree = ttk.Treeview(report_frame, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.report_tree.yview)
        self.report_tree.pack(fill='both', expand=True)
    
    def create_customer_history_tab(self):
        tab = tk.Frame(self.notebook, bg='#ecf0f1')
        self.notebook.add(tab, text='Customer History')
        
        # Customer selection
        top_frame = tk.Frame(tab, bg='#ecf0f1')
        top_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(top_frame, text="Select Customer:", bg='#ecf0f1', font=('Arial', 12)).pack(side='left', padx=5)
        self.history_customer = ttk.Combobox(top_frame, width=40, state='readonly')
        self.history_customer.pack(side='left', padx=5)
        self.load_customers_for_history()
        
        tk.Button(top_frame, text="View History", command=self.view_customer_history,
                 bg='#27ae60', fg='white').pack(side='left', padx=5)
        
        # Customer info display
        info_frame = tk.LabelFrame(tab, text="Customer Information", bg='#ecf0f1', padx=10, pady=10)
        info_frame.pack(fill='x', padx=10, pady=10)
        
        self.customer_info = tk.Text(info_frame, height=5, bg='white')
        self.customer_info.pack(fill='x')
        
        # History display
        history_frame = tk.LabelFrame(tab, text="Purchase History", bg='#ecf0f1', padx=10, pady=10)
        history_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.history_text = tk.Text(history_frame, bg='white')
        self.history_text.pack(fill='both', expand=True)
    
    def show_sales_summary(self):
        self.report_tree.delete(*self.report_tree.get_children())
        self.report_tree['columns'] = ('Product', 'Category', 'Price', 'Stock')
        self.report_tree['show'] = 'headings'
        
        self.report_tree.heading('Product', text='Product Name')
        self.report_tree.heading('Category', text='Category')
        self.report_tree.heading('Price', text='Price')
        self.report_tree.heading('Stock', text='Current Stock')
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.product_name, c.category_name, p.product_price, p.product_number
                FROM Product_Details p
                JOIN Product_Category c ON p.category_id = c.category_id
                ORDER BY p.product_name
            """)
            for row in cursor.fetchall():
                self.report_tree.insert('', 'end', values=row)
            conn.close()
    
    def show_low_stock(self):
        self.report_tree.delete(*self.report_tree.get_children())
        self.report_tree['columns'] = ('Product', 'Category', 'Stock', 'Status')
        self.report_tree['show'] = 'headings'
        
        self.report_tree.heading('Product', text='Product Name')
        self.report_tree.heading('Category', text='Category')
        self.report_tree.heading('Stock', text='Stock Level')
        self.report_tree.heading('Status', text='Status')
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.product_name, c.category_name, p.product_number,
                CASE 
                    WHEN p.product_number = 0 THEN 'OUT OF STOCK'
                    WHEN p.product_number < 10 THEN 'LOW STOCK'
                    ELSE 'REORDER SOON'
                END as status
                FROM Product_Details p
                JOIN Product_Category c ON p.category_id = c.category_id
                WHERE p.product_number < 20
                ORDER BY p.product_number
            """)
            for row in cursor.fetchall():
                self.report_tree.insert('', 'end', values=row)
            conn.close()
    
    def show_customer_report(self):
        self.report_tree.delete(*self.report_tree.get_children())
        self.report_tree['columns'] = ('Name', 'Type', 'Points', 'Contact', 'Email')
        self.report_tree['show'] = 'headings'
        
        self.report_tree.heading('Name', text='Customer Name')
        self.report_tree.heading('Type', text='Type')
        self.report_tree.heading('Points', text='Loyalty Points')
        self.report_tree.heading('Contact', text='Contact')
        self.report_tree.heading('Email', text='Email')
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT customer_name, customer_type, loyalty_points, customer_contact, customer_email
                FROM Customer_Details
                ORDER BY loyalty_points DESC
            """)
            for row in cursor.fetchall():
                self.report_tree.insert('', 'end', values=row)
            conn.close()
    
    def load_customers_for_history(self):
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id, customer_name FROM Customer_Details")
            customers = [f"{row[0]} - {row[1]}" for row in cursor.fetchall()]
            self.history_customer['values'] = customers
            conn.close()
    
    def view_customer_history(self):
        customer = self.history_customer.get()
        if not customer:
            messagebox.showerror("Error", "Please select a customer")
            return
        
        customer_id = int(customer.split(' - ')[0])
        
        conn = self.system.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Customer_Details WHERE customer_id=%s", (customer_id,))
            cust_data = cursor.fetchone()
            conn.close()
            
            if cust_data:
                self.customer_info.delete('1.0', 'end')
                info = f"Customer ID: {cust_data[0]}\n"
                info += f"Name: {cust_data[1]}\n"
                info += f"Contact: {cust_data[2]}\n"
                info += f"Email: {cust_data[3]}\n"
                info += f"Type: {cust_data[4]}\n"
                info += f"Loyalty Points: {cust_data[5]}\n"
                self.customer_info.insert('1.0', info)
                
                self.history_text.delete('1.0', 'end')
                self.history_text.insert('1.0', "Purchase history functionality can be extended by creating a Transactions table.\nThis would store all checkout records with timestamps and product details.")
    
    def logout(self):
        self.root.destroy()
        system = NexusTechSystem()
        LoginWindow(system).run()

# Database setup SQL script (run this first in MySQL)
"""
CREATE DATABASE IF NOT EXISTS nexus_tech;
USE nexus_tech;

CREATE TABLE IF NOT EXISTS Staff_Details (
    staff_id INT PRIMARY KEY AUTO_INCREMENT,
    staff_name VARCHAR(100) NOT NULL,
    staff_password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS Product_Category (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS Customer_Details (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_name VARCHAR(100) NOT NULL,
    customer_contact VARCHAR(20),
    customer_email VARCHAR(100),
    customer_type ENUM('Basic', 'Premium', 'Student') DEFAULT 'Basic',
    loyalty_points INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Product_Details (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(200) NOT NULL,
    category_id INT,
    product_price DECIMAL(10,2) NOT NULL,
    product_number INT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES Product_Category(category_id)
);

-- Insert sample data
INSERT INTO Staff_Details (staff_name, staff_password) VALUES 
('admin', SHA2('admin123', 256)),
('john', SHA2('staff123', 256));

INSERT INTO Product_Category (category_name) VALUES 
('Laptops'), ('Smartphones'), ('Accessories'), ('Components');

INSERT INTO Customer_Details (customer_name, customer_contact, customer_email, customer_type, loyalty_points) VALUES
('Alice Johnson', '123-456-7890', 'alice@email.com', 'Premium', 250),
('Bob Smith', '234-567-8901', 'bob@email.com', 'Basic', 50),
('Carol White', '345-678-9012', 'carol@email.com', 'Student', 100);

INSERT INTO Product_Details (product_name, category_id, product_price, product_number) VALUES
('Dell XPS 15', 1, 1299.99, 15),
('MacBook Pro', 1, 1999.99, 8),
('iPhone 15', 2, 999.99, 25),
('Samsung Galaxy S24', 2, 899.99, 5),
('Wireless Mouse', 3, 29.99, 50),
('USB-C Cable', 3, 12.99, 3);
"""

# Main program
if __name__ == "__main__":
    print("Starting Nexus Tech System...")
    system = NexusTechSystem()
    print("System initialized")
    login_window = LoginWindow(system)
    print("Login window created")
    login_window.root.mainloop()
    system = NexusTechSystem()
    login_window = LoginWindow(system)
    login_window.root.mainloop()
