import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

DB_FILE = "shop.db"


# ---------- 创建数据库和表 ----------
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


# ---------- 主窗口 ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple Product Manager")
        self.geometry("900x600")

        # 整个程序只用一个数据库连接
        self.conn = sqlite3.connect(DB_FILE)

        # 把页面放进来
        self.page = ProductPage(self, self.conn)
        self.page.pack(fill="both", expand=True)

        # 关闭窗口时，把数据库连接也关掉
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.conn.close()
        self.destroy()


# ---------- 产品管理页面 ----------
class ProductPage(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn

        # 标题
        ttk.Label(self, text="Product Management",
                  font=("Helvetica", 16, "bold")).pack(pady=10)

        # 低库存提示（红色），一开始先显示“都正常”
        self.low_stock_label = ttk.Label(
            self,
            text="All stock levels are OK.",
            foreground="red"
        )
        self.low_stock_label.pack(pady=5)

        # 刷新按钮
        ttk.Button(self, text="Refresh", command=self.load_products).pack(pady=5)

        # 产品表格
        columns = ("id", "category", "name", "price", "stock")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, anchor="center", width=150)
        self.tree.pack(fill="both", padx=10, pady=5)

        # 点击表格中的一行时，把数据放到下面的输入框里
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # 输入区域
        form = ttk.Frame(self)
        form.pack(padx=10, pady=5)

        ttk.Label(form, text="Category:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.cat_entry = ttk.Entry(form, width=20)
        self.cat_entry.grid(row=0, column=1, padx=5, pady=3)

        ttk.Label(form, text="Name:").grid(row=0, column=2, sticky="e", padx=5, pady=3)
        self.name_entry = ttk.Entry(form, width=20)
        self.name_entry.grid(row=0, column=3, padx=5, pady=3)

        ttk.Label(form, text="Price:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        self.price_entry = ttk.Entry(form, width=20)
        self.price_entry.grid(row=1, column=1, padx=5, pady=3)

        ttk.Label(form, text="Stock:").grid(row=1, column=2, sticky="e", padx=5, pady=3)
        self.stock_entry = ttk.Entry(form, width=20)
        self.stock_entry.grid(row=1, column=3, padx=5, pady=3)

        # 按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Add Product",
                   command=self.add_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Update Selected",
                   command=self.update_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Selected",
                   command=self.delete_product).pack(side="left", padx=5)

        # 先加载一次数据
        self.load_products()

    # ---------- 小工具：执行 SQL ----------
    def run_sql(self, sql, params=(), fetch=False):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        self.conn.commit()

    # ---------- 加载表格 + 检查低库存 ----------
    def load_products(self):
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self.run_sql(
            "SELECT id, category, name, price, stock FROM products ORDER BY id",
            fetch=True
        ) or []

        for r in rows:
            self.tree.insert(
                "",
                "end",
                values=(r[0], r[1], r[2], f"{r[3]:.2f}" if r[3] is not None else "", r[4])
            )

        # 每次加载完都检查一次低库存
        self.check_low_stock()

    def check_low_stock(self):
        """
        查找库存少于 10 的商品。
        如果有，就在顶部红字提示；如果没有，就显示“都正常”。
        """
        rows = self.run_sql(
            "SELECT name, stock FROM products WHERE stock IS NOT NULL AND stock < 10",
            fetch=True
        ) or []

        if not rows:
            self.low_stock_label.config(text="All stock levels are OK.")
        else:
            # rows 里是 (name, stock) 的列表
            parts = [f"{name} (stock: {stock})" for (name, stock) in rows]
            text = "⚠ Low stock (<10): " + ";  ".join(parts)
            self.low_stock_label.config(text=text)

    # ---------- 选中表格行，填充到输入框 ----------
    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
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

    # ---------- 新增 ----------
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

        self.run_sql(
            "INSERT INTO products (category, name, price, stock) VALUES (?, ?, ?, ?)",
            (cat, name, price, stock)
        )
        self.load_products()

    # ---------- 更新 ----------
    def update_product(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a product to update.")
            return

        product_id = self.tree.item(sel[0], "values")[0]

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

        self.run_sql(
            "UPDATE products SET category=?, name=?, price=?, stock=? WHERE id=?",
            (cat, name, price, stock, product_id)
        )
        self.load_products()

    # ---------- 删除 ----------
    def delete_product(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a product to delete.")
            return

        values = self.tree.item(sel[0], "values")
        product_id, _, name, _, _ = values

        if not messagebox.askyesno("Confirm", f"Delete product '{name}'?"):
            return

        self.run_sql("DELETE FROM products WHERE id=?", (product_id,))
        self.load_products()


# ---------- 入口 ----------
if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
