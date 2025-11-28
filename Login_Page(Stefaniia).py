import tkinter as tk
from tkinter import messagebox

# COLORS / STYLE
BG_GRADIENT = "#0e0e10"       # фон окна (почти чёрный с фиолетовым)
CARD_COLOR = "#1a1b26"        # карточки
TEXT_LIGHT = "#ffffff"        # основной текст
ACCENT = "#7d5fff"            # основной акцент (фиолетовый)
ACCENT_HOVER = "#9b87ff"      # подсветка кнопок
GLOW = "#4b39bb"              # цвет рамки вокруг карточек

# Login Passwords 
USERS = {
    "admin": {"admin": "1234"},
    "staff": {"staff": "5678"}
}
current_role = None
LOGO = None   # сюда загрузим картинку после создания root
# loading Logo
def load_logo():
    global LOGO
    try:
        LOGO = tk.PhotoImage(file="nexus_logo.png")
    except Exception:
        LOGO = None
#Page 1:
    def open_role_window():
    global current_role
    current_role = None
    for widget in root.winfo_children():
        widget.destroy()
    frame = tk.Frame(root, bg=BG_GRADIENT)
    frame.pack(expand=True, fill="both")
    # LOGO
    if LOGO is not None:
        logo_label = tk.Label(frame, image=LOGO, bg=BG_GRADIENT)
        logo_label.pack(pady=(25, 5))
    # Slogan
    slogan = tk.Label(
        frame,
        text="NEXUS TECHSHOP",
        font=("Arial", 16, "bold"),
        fg=TEXT_LIGHT,
        bg=BG_GRADIENT
    )
    slogan.pack()

    subtitle = tk.Label(
        frame,
        text="Powering your tech universe",
        font=("Arial", 10, "italic"),
        fg="#b0b3b8",
        bg=BG_GRADIENT
    )
    subtitle.pack(pady=(0, 25))

    # hover для обычных Button
    def hover(event, btn):
        btn.config(bg=ACCENT_HOVER)

    def leave(event, btn):
        btn.config(bg=ACCENT)

    btn_admin = tk.Button(
        frame,
        text="I am Admin",
        font=("Arial", 13, "bold"),
        bg=ACCENT,
        fg="white",
        width=18,
        height=2,
        bd=0,
        relief="flat",
        activebackground=ACCENT_HOVER,
        activeforeground="white",
        command=lambda: open_login_window("admin")
    )
    btn_admin.pack(pady=8)

    btn_staff = tk.Button(
        frame,
        text="I am Staff",
        font=("Arial", 13, "bold"),
        bg=ACCENT,
        fg="white",
        width=18,
        height=2,
        bd=0,
        relief="flat",
        activebackground=ACCENT_HOVER,
        activeforeground="white",
        command=lambda: open_login_window("staff")
    )
    btn_staff.pack(pady=8)

    btn_admin.bind("<Enter>", lambda e: hover(e, btn_admin))
    btn_admin.bind("<Leave>", lambda e: leave(e, btn_admin))
    btn_staff.bind("<Enter>", lambda e: hover(e, btn_staff))
    btn_staff.bind("<Leave>", lambda e: leave(e, btn_staff))

    footer = tk.Label(
        frame,
        text="Secure access portal · Nexus Techshop",
        font=("Arial", 9, "italic"),
        fg="#777b80",
        bg=BG_GRADIENT
    )
    footer.pack(side="bottom", pady=10)
# Window to create the account
def open_create_account_window(role):
    win = tk.Toplevel(root)
    win.title(f"Create {role.capitalize()} Account")
    win.configure(bg=BG_GRADIENT)
    win.geometry("330x270")
    win.resizable(False, False)

    card = tk.Frame(
        win,
        bg=CARD_COLOR,
        padx=15, pady=15,
        highlightthickness=2,
        highlightbackground=GLOW,
        highlightcolor=GLOW
    )
    card.pack(pady=20, padx=15, fill="both", expand=True)

    tk.Label(
        card,
        text=f"New {role.capitalize()} Account",
        font=("Arial", 14, "bold"),
        fg=TEXT_LIGHT,
        bg=CARD_COLOR
    ).pack(pady=(0, 10))
    tk.Label(card, text="New username:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 10)).pack(anchor="w")
    entry_user = tk.Entry(card, font=("Arial", 10), width=25)
    entry_user.pack(pady=3)
    tk.Label(card, text="New password:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 10)).pack(anchor="w")
    entry_pass = tk.Entry(card, font=("Arial", 10), width=25, show="*")
    entry_pass.pack(pady=3)

    tk.Label(card, text="Confirm password:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 10)).pack(anchor="w")
    entry_confirm = tk.Entry(card, font=("Arial", 10), width=25, show="*")
    entry_confirm.pack(pady=3)

    lbl_msg = tk.Label(card, text="", fg="#ff6961",
                       bg=CARD_COLOR, font=("Arial", 9, "italic"))
    lbl_msg.pack(pady=3)

    def create_account():
        username = entry_user.get().strip()
        password = entry_pass.get()
        confirm = entry_confirm.get()

        if not username or not password or not confirm:
            lbl_msg.config(text="All fields are required.")
            return
        if username in USERS[role]:
            lbl_msg.config(text="Username already exists.")
            return
        if password != confirm:
            lbl_msg.config(text="Passwords do not match.")
            return
        if len(password) < 4:
            lbl_msg.config(text="Password must be at least 4 characters.")
            return

        USERS[role][username] = password
        messagebox.showinfo("Account created",
                            f"New {role} account '{username}' created.")
        win.destroy()

    btn_create = tk.Button(
        card,
        text="Create account",
        font=("Arial", 11, "bold"),
        bg=ACCENT,
        fg="white",
        width=18,
        bd=0,
        relief="flat",
        activebackground=ACCENT_HOVER,
        activeforeground="white",
        command=create_account
    )
    btn_create.pack(pady=8)
# Window to change the password

def open_change_password_window(role):
    win = tk.Toplevel(root)
    win.title(f"Change {role.capitalize()} Password")
    win.configure(bg=BG_GRADIENT)
    win.geometry("330x300")
    win.resizable(False, False)

    card = tk.Frame(
        win,
        bg=CARD_COLOR,
        padx=15, pady=15,
        highlightthickness=2,
        highlightbackground=GLOW,
        highlightcolor=GLOW
    )
    card.pack(pady=20, padx=15, fill="both", expand=True)

    tk.Label(
        card,
        text=f"Change {role.capitalize()} Password",
        font=("Arial", 14, "bold"),
        fg=TEXT_LIGHT,
        bg=CARD_COLOR
    ).pack(pady=(0, 10))

    tk.Label(card, text="Username:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 10)).pack(anchor="w")
    entry_user = tk.Entry(card, font=("Arial", 10), width=25)
    entry_user.pack(pady=3)

    tk.Label(card, text="Current password:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 10)).pack(anchor="w")
    entry_old = tk.Entry(card, font=("Arial", 10), width=25, show="*")
    entry_old.pack(pady=3)

    tk.Label(card, text="New password:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 10)).pack(anchor="w")
    entry_new = tk.Entry(card, font=("Arial", 10), width=25, show="*")
    entry_new.pack(pady=3)

    tk.Label(card, text="Confirm new password:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 10)).pack(anchor="w")
    entry_confirm = tk.Entry(card, font=("Arial", 10), width=25, show="*")
    entry_confirm.pack(pady=3)

    lbl_msg = tk.Label(card, text="", fg="#ff6961",
                       bg=CARD_COLOR, font=("Arial", 9, "italic"))
    lbl_msg.pack(pady=3)

    def change_password():
        username = entry_user.get().strip()
        old = entry_old.get()
        new = entry_new.get()
        confirm = entry_confirm.get()

        if not username or not old or not new or not confirm:
            lbl_msg.config(text="All fields are required.")
            return

        if username not in USERS[role]:
            lbl_msg.config(text="User not found.")
            return

        if USERS[role][username] != old:
            lbl_msg.config(text="Current password is incorrect.")
            return

        if new != confirm:
            lbl_msg.config(text="New passwords do not match.")
            return

        if len(new) < 4:
            lbl_msg.config(text="New password must be at least 4 characters.")
            return

        USERS[role][username] = new
        messagebox.showinfo("Password changed",
                            "Password updated successfully.")
        win.destroy()

    btn_change = tk.Button(
        card,
        text="Change password",
        font=("Arial", 11, "bold"),
        bg=ACCENT,
        fg="white",
        width=18,
        bd=0,
        relief="flat",
        activebackground=ACCENT_HOVER,
        activeforeground="white",
        command=change_password
    )
    btn_change.pack(pady=8)
# ======================================================
# Page 2: Login for chosen role
# ======================================================
def open_login_window(role):
    global current_role
    current_role = role

    for widget in root.winfo_children():
        widget.destroy()

    frame = tk.Frame(root, bg=BG_GRADIENT)
    frame.pack(expand=True, fill="both")

    # logo on top
    if LOGO is not None:
        logo_label = tk.Label(frame, image=LOGO, bg=BG_GRADIENT)
        logo_label.pack(pady=(20, 5))

    tk.Label(
        frame,
        text="NEXUS TECHSHOP",
        font=("Arial", 14, "bold"),
        fg=TEXT_LIGHT,
        bg=BG_GRADIENT
    ).pack()

    tk.Label(
        frame,
        text=f"{role.capitalize()} login",
        font=("Arial", 10, "italic"),
        fg="#b0b3b8",
        bg=BG_GRADIENT
    ).pack(pady=(0, 10))

    card = tk.Frame(
        frame,
        bg=CARD_COLOR,
        padx=20, pady=20,
        highlightthickness=2,
        highlightbackground=GLOW,
        highlightcolor=GLOW
    )
    card.pack(pady=10)

    tk.Label(
        card,
        text=f"{role.upper()} LOGIN",
        font=("Arial", 16, "bold"),
        fg=TEXT_LIGHT,
        bg=CARD_COLOR
    ).pack(pady=(0, 10))

    tk.Label(card, text="Username:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 11)).pack(anchor="w")
    entry_user = tk.Entry(card, font=("Arial", 11), width=25)
    entry_user.pack(pady=4)

    tk.Label(card, text="Password:", fg=TEXT_LIGHT,
             bg=CARD_COLOR, font=("Arial", 11)).pack(anchor="w")
    entry_pass = tk.Entry(card, font=("Arial", 11), width=25, show="*")
    entry_pass.pack(pady=4)

    show_var = tk.BooleanVar(value=False)

    def toggle_password():
        entry_pass.config(show="" if show_var.get() else "*")

    chk_show = tk.Checkbutton(
        card,
        text="Show password",
        variable=show_var,
        command=toggle_password,
        bg=CARD_COLOR,
        fg="#b0b3b8",
        activebackground=CARD_COLOR,
        activeforeground="#b0b3b8",
        selectcolor=CARD_COLOR,
        font=("Arial", 9)
    )
    chk_show.pack(anchor="w", pady=(0, 4))

    lbl_error = tk.Label(
        card,
        text="",
        fg="#ff6961",
        bg=CARD_COLOR,
        font=("Arial", 9, "italic")
    )
    lbl_error.pack(pady=(0, 4))

    def do_login():
        username = entry_user.get().strip()
        password = entry_pass.get()
        lbl_error.config(text="")

        if username in USERS(role) and USERS(role)(username) == password:
            messagebox.showinfo("Welcome",
                                f"Welcome to Nexus, {role.capitalize()}!")
        else:
            lbl_error.config(text="Incorrect username or password.")

    btn_login = tk.Button(
        card,
        text="Login",
        font=("Arial", 12, "bold"),
        bg=ACCENT,
        fg="white",
        width=20,
        bd=0,
        relief="flat",
        activebackground=ACCENT_HOVER,
        activeforeground="white",
        command=do_login
    )
    btn_login.pack(pady=6)
    btn_forgot = tk.Button(
        card,
        text="Forgot username/password?",
        font=("Arial", 9, "underline"),
        bg=CARD_COLOR,
        fg="#9aa0a6",
        bd=0,
        activebackground=CARD_COLOR,
        activeforeground="white",
        cursor="hand2",
        command=lambda: messagebox.showinfo(
            "Recover Account",
            "Please contact Nexus admin to reset your login details."
        )
    )
    btn_forgot.pack(pady=(0, 4))
    # Create account / Change password
    links = tk.Frame(card, bg=CARD_COLOR)
    links.pack(pady=2)
    btn_create = tk.Button(
        links,
        text="Create account",
        font=("Arial", 9),
        bg=CARD_COLOR,
        fg="#9aa0a6",
        bd=0,
        activebackground=CARD_COLOR,
        activeforeground="white",
        cursor="hand2",
        command=lambda: open_create_account_window(role)
    )
    btn_create.grid(row=0, column=0, padx=5)
    btn_change = tk.Button(
        links,
        text="Change password",
        font=("Arial", 9),
        bg=CARD_COLOR,
        fg="#9aa0a6",
        bd=0,
        activebackground=CARD_COLOR,
        activeforeground="white",
        cursor="hand2",
        command=lambda: open_change_password_window(role)
    )
    btn_change.grid(row=0, column=1, padx=5)

    # BACK
    btn_back = tk.Button(
        frame,
        text="← Back to role select",
        font=("Arial", 10),
        bg=ACCENT,
        fg="white",
        width=20,
        bd=0,
        relief="flat",
        activebackground=ACCENT_HOVER,
        activeforeground="white",
        command=open_role_window
    )
    btn_back.pack(pady=10)
# ======================================================
# SPLASH SCREEN (ЗАГРУЗКА)
# ======================================================
def splash_screen():
    splash = tk.Toplevel()
    splash.title("Nexus Loading")
    splash.geometry("360x260")
    splash.overrideredirect(True)
    splash.configure(bg=BG_GRADIENT)

    # центрируем
    splash.update_idletasks()
    w = splash.winfo_width()
    h = splash.winfo_height()
    ws = splash.winfo_screenwidth()
    hs = splash.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    splash.geometry(f"+{x}+{y}")

    if LOGO is not None:
        logo_label = tk.Label(splash, image=LOGO, bg=BG_GRADIENT)
        logo_label.pack(pady=(30, 10))

    title = tk.Label(
        splash,
        text="NEXUS TECHSHOP",
        font=("Arial", 16, "bold"),
        fg=TEXT_LIGHT,
        bg=BG_GRADIENT
    )
    title.pack()

    slogan = tk.Label(
        splash,
        text="Powering your tech universe",
        font=("Arial", 10, "italic"),
        fg="#b0b3b8",
        bg=BG_GRADIENT
    )
    slogan.pack(pady=(0, 15))

    loading = tk.Label(
        splash,
        text="Loading Nexus system...",
        font=("Arial", 10),
        fg="#b0b3b8",
        bg=BG_GRADIENT
    )
    loading.pack()

    # через 1.8 сек закрываем splash и открываем выбор роли
    root.after(1800, lambda: (splash.destroy(), open_role_window()))
# ======================================================
# ROOT WINDOW
# ======================================================
root = tk.Tk()
root.title("Nexus Techshop Login")
root.geometry("430x520")
root.resizable(False, False)
root.configure(bg=BG_GRADIENT)
load_logo()
splash_screen()
root.mainloop()
