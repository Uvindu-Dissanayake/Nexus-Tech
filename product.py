import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

DB_FILE = "shop.db"


# ---------- 初始化数据库，只包含 products 表 ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
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


# ---------- 主应用 ----------
class ProductApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple Product Manager")
        self.geometry("900x600")

        # 建立数据库连接（程序整个生命周期共用）
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row

        self.page = ProductPage(self, self.conn)
        self.page.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.conn.close()
        self.destroy()


# ---------- 产品管理页面 ----------
class ProductPage(ttk.Frame):
    """
    简单版产品管理界面：
    - 显示所有产品（id, category, name, price, stock）
    - 可以新增、更新、删除产品
    - 库存少于 10 会在顶部右侧红色提示
    """
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn

        ttk.Label(self, text="Product Management",
                  font=("Helvetica", 16, "bold")).pack(pady=10)

        # 顶部区域：左边 Refresh 按钮，右边低库存提示
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)

        ttk.Button(top, text="Refresh", command=self.load_products).pack(
            side="left", padx=5
        )

        # 低库存提示 Label 放在顶部右侧
        self.low_stock_label = ttk.Label(
            top,
            text="All stock levels are OK.",
            foreground="red"
        )
        self.low_stock_label.pack(side="right", padx=5)

        # 中间表格
        columns = ("id", "category", "name", "price", "stock")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=18)
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, anchor="center", width=150)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # 选中行时，把数据填到输入框
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # 下方输入框
        form = ttk.Frame(self)
        form.pack(fill="x", padx=10, pady=5)

        ttk.Label(form, text="Category:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.cat_entry = ttk.Entry(form, width=20)
        self.cat_entry.grid(row=0, column=1, padx=5, pady=3)

        ttk.Label(form, text="Name:").grid(row=0, column=2, sticky="e", padx=5, pady=3)
        self.name_entry = ttk.Entry(form, width=30)
        self.name_entry.grid(row=0, column=3, padx=5, pady=3)

        ttk.Label(form, text="Price:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        self.price_entry = ttk.Entry(form, width=20)
        self.price_entry.grid(row=1, column=1, padx=5, pady=3)

        ttk.Label(form, text="Stock:").grid(row=1, column=2, sticky="e", padx=5, pady=3)
        self.stock_entry = ttk.Entry(form, width=20)
        self.stock_entry.grid(row=1, column=3, padx=5, pady=3)

        # 按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="Add Product",
                   command=self.add_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Update Selected",
                   command=self.update_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Selected",
                   command=self.delete_product).pack(side="left", padx=5)

        # 初始化加载一次
        self.load_products()

    # --------- 共用的小工具：执行 SQL ----------
    def run_query(self, sql, params=(), fetch=False):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        if fetch:
            rows = cur.fetchall()
            return rows
        self.conn.commit()

    # --------- 加载数据 & 检查低库存 ----------
    def load_products(self):
        # 清空表格
        for row in self.tree.get_children():
            self.tree.delete(row)

        rows = self.run_query(
            "SELECT id, category, name, price, stock FROM products ORDER BY id",
            fetch=True
        ) or []

        for r in rows:
            self.tree.insert(
                "", "end",
                values=(
                    r["id"],
                    r["category"],
                    r["name"],
                    f"{r['price']:.2f}" if r["price"] is not None else "",
                    r["stock"]
                )
            )

        self.check_low_stock()

    def check_low_stock(self):
        """库存少于 10 的产品提示"""
        rows = self.run_query(
            "SELECT name, stock FROM products WHERE stock IS NOT NULL AND stock < 10",
            fetch=True
        ) or []

        if not rows:
            self.low_stock_label.config(text="All stock levels are OK.")
            return

        msg_lines = [f"{r['name']} (stock: {r['stock']})" for r in rows]
        msg = "⚠ Low stock (<10): " + ";  ".join(msg_lines)
        self.low_stock_label.config(text=msg)

    # --------- 选中行 -> 填充输入框 ----------
    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0])["values"]
        # values: (id, category, name, price, stock)
        _, category, name, price, stock = values
        self.cat_entry.delete(0, "end")
        self.cat_entry.insert(0, category)
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, name)
        self.price_entry.delete(0, "end")
        self.price_entry.insert(0, price)
        self.stock_entry.delete(0, "end")
        self.stock_entry.insert(0, stock)

    # --------- 新增 ----------
    def add_product(self):
        cat = self.cat_entry.get().strip()
        name = self.name_entry.get().strip()
        price_str = self.price_entry.get().strip()
        stock_str = self.stock_entry.get().strip() or "0"

        if not cat or not name or not price_str:
            messagebox.showwarning("Missing", "Category, Name and Price are required.")
            return

        try:
            price = float(price_str)
        except ValueError:
            messagebox.showerror("Error", "Price must be a number.")
            return

        try:
            stock = int(stock_str)
        except ValueError:
            messagebox.showerror("Error", "Stock must be an integer.")
            return

        self.run_query(
            "INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
            (cat, name, price, stock)
        )
        messagebox.showinfo("Success", "Product added.")
        self.load_products()

    # --------- 更新 ----------
    def update_product(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a product to update.")
            return

        values = self.tree.item(sel[0])["values"]
        product_id = values[0]

        cat = self.cat_entry.get().strip()
        name = self.name_entry.get().strip()
        price_str = self.price_entry.get().strip()
        stock_str = self.stock_entry.get().strip()

        if not cat or not name or not price_str or not stock_str:
            messagebox.showwarning("Missing", "All fields are required.")
            return

        try:
            price = float(price_str)
        except ValueError:
            messagebox.showerror("Error", "Price must be a number.")
            return

        try:
            stock = int(stock_str)
        except ValueError:
            messagebox.showerror("Error", "Stock must be an integer.")
            return

        self.run_query(
            "UPDATE products SET category=?, name=?, price=?, stock=? WHERE id=?",
            (cat, name, price, stock, product_id)
        )
        messagebox.showinfo("Success", "Product updated.")
        self.load_products()

    # --------- 删除 ----------
    def delete_product(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a product to delete.")
            return

        values = self.tree.item(sel[0])["values"]
        product_id, _, name, _, _ = values

        if not messagebox.askyesno("Confirm", f"Delete product '{name}'?"):
            return

        self.run_query("DELETE FROM products WHERE id=?", (product_id,))
        messagebox.showinfo("Deleted", "Product deleted.")
        self.load_products()


if __name__ == "__main__":
    init_db()
    app = ProductApp()
    app.mainloop()
