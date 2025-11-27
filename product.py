import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

DB_FILE = "shop.db"
#tkinter：Python 自带的图形界面库，tk 是窗口控件（Button、Label 等）的前缀。
#ttk：tkinter 的“美化版控件”，外观更好看一点。
#messagebox：弹出提示框（警告、错误、信息）的模块。
#sqlite3：内置的轻量级数据库，不需要安装服务器，直接用一个文件当数据库。
#DB_FILE = "shop.db"：指定数据库文件名，后面连库都用这个


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
#sqlite3.connect(DB_FILE)：连上 shop.db，如果文件不存在会自动创建。
#cursor()：获取一个“游标”，用来执行 SQL 语句。
#CREATE TABLE IF NOT EXISTS：如果没有 products 这张表，就创建：
#id：主键，自增。
#commit()：提交更改。
#close()：关闭连接。


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
#class App(tk.Tk)：定义一个类，继承 tk.Tk，也就是整个主窗口。
#super().__init__()：调用父类构造函数，创建窗口。
#self.title(...) / self.geometry(...)：设置标题、窗口大小。
#self.conn：创建一个数据库连接，整个程序共享这一条连接。
#ProductPage(self, self.conn)：创建一个“产品管理页面”对象。
#pack(fill="both", expand=True)：让页面充满整个窗口。
#protocol("WM_DELETE_WINDOW", self.on_close)：点右上角关闭按钮时，先执行 on_close：关闭数据库连接；销毁窗口。
# ---------- 产品管理页面 ----------
class ProductPage(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        # 标题
        ttk.Label(self, text="Product Management",
                  font=("Helvetica", 16, "bold")).pack(pady=10)
# 继承 ttk.Frame：是一个“页面/容器”。
#parent：就是 App 主窗口。
#self.conn = conn：保存从 App 传进来的数据库连接。
#Label：标题文字

        # 低库存提示（红色），一开始先显示“都正常”
        self.low_stock_label = ttk.Label(
            self,
            text="All stock levels are OK.",
            foreground="red"
        )
        self.low_stock_label.pack(pady=5)

        # 刷新按钮
        ttk.Button(self, text="Refresh", command=self.load_products).pack(pady=5)
#low_stock_label：红色字体的标签，用来显示低库存信息。
#一开始文字是 "All stock levels are OK."。
#Refresh 按钮：点击就调用 self.load_products() 重新从数据库读取数据 + 更新低库存提示。

        # 产品表格
        columns = ("id", "category", "name", "price", "stock")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, anchor="center", width=150)
        self.tree.pack(fill="both", padx=10, pady=5)

        # 点击表格中的一行时，把数据放到下面的输入框里
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
#Treeview：一个表格控件。
#columns：定义列名。
#show="headings"：只显示标题，不显示树形的第一列。
#heading：设置每一列的标题文字。
#column：设置对齐方式、列宽。
#bind("<<TreeviewSelect>>", self.on_select)：
#当用户点选了一行，触发 on_select 函数，把数据放进下面的输入框里。

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
#用一个 Frame 把下面的标签和输入框装在一起。
#grid(row=?, column=?)：表格布局，按行列摆放。
#4个字段：Category / Name / Price / Stock。

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
       # 三个按钮分别绑定三个方法：

#add_product：新增一条记录。
#update_product：修改选中的那一条。
#delete_product：删除选中的那一条。
#load_products()：页面创建好之后立刻从数据库读一次数据，填满表格，并检查低库存。

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
