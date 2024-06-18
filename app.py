import customtkinter as ctk
import uuid
import os
import subprocess
import sys
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from tkinter import ttk
import sqlite3
import bcrypt

def setup_database():
    conn = sqlite3.connect('receipts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password BLOB)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed, user_input):
    return bcrypt.checkpw(user_input.encode('utf-8'), hashed)

def register_user(username, password):
    hashed = hash_password(password)
    conn = sqlite3.connect('receipts.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
    conn.commit()
    conn.close()

def validate_user(username, password):
    conn = sqlite3.connect('receipts.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()
    if data and check_password(data[0], password):
        return True
    else:
        return False

class ReceiptViewerScreen(ctk.CTkFrame):
    def __init__(self, master, switch_to_main, **kwargs):
        super().__init__(master, **kwargs)
        self.switch_to_main = switch_to_main
        self.selected_receipt_id = None
        self.receipt_df = pd.DataFrame()

        self.label = ctk.CTkLabel(self, text="Receipts")
        self.label.pack(pady=12, padx=10)

        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(pady=12, padx=10, fill="both", expand=True)

        self.load_receipts()

        self.print_button = ctk.CTkButton(self, text="Print Receipt", command=self.print_receipt)
        self.print_button.pack(pady=12, padx=10)

        self.back_button = ctk.CTkButton(self, text="Back to Main", command=switch_to_main)
        self.back_button.pack(pady=12, padx=10)

    def load_receipts(self):
        self.clear_table()

        csv_file = os.path.join(os.path.dirname(__file__), 'receipts.csv')
        try:
            if os.path.exists(csv_file):
                self.receipt_df = pd.read_csv(csv_file)
                print(f"Loaded {len(self.receipt_df)} receipts from CSV.")
                self.create_table()
            else:
                print("Receipts CSV file not found.")
        except Exception as e:
            print(f"Error loading receipt data: {e}")

    def clear_table(self):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

    def create_table(self):
        columns = ("ID", "Name", "Date", "Amount", "Amount Fig", "Invoice No", "Being payed for")
        self.table = ttk.Treeview(self.table_frame, columns=columns, show='headings', style="Custom.Treeview")
        
        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, anchor='center')

        for index, row in self.receipt_df.iterrows():
            self.table.insert("", "end", values=(row['ID'], row['Name'], row['Date'], row['Amount'], row['Amount Fig'], row['Invoice No'], row['Being payed for']))

        self.table.bind('<<TreeviewSelect>>', self.on_row_select)
        self.table.pack(fill="both", expand=True)

        # Custom style for the Treeview
        style = ttk.Style()
        style.configure("Custom.Treeview", font=('Helvetica', 14))
        style.configure("Custom.Treeview.Heading", font=('Helvetica', 16, 'bold'))

    def on_row_select(self, event):
        selected_item = self.table.selection()
        if selected_item:
            item = self.table.item(selected_item)
            self.selected_receipt_id = item['values'][0]
            print(f"Selected Receipt ID: {self.selected_receipt_id}")

    def print_receipt(self):
        if not self.selected_receipt_id:
            print("No receipt selected.")
            return

        receipt_image_path = os.path.join(os.path.dirname(__file__), "receipts", f"{self.selected_receipt_id}.png")
        if os.path.exists(receipt_image_path):
            try:
                if sys.platform == "win32":
                    subprocess.run(["start", "/wait", "", "mspaint", "/pt", receipt_image_path], shell=True)
                else:
                    print("Printing not supported on this platform.")
            except Exception as e:
                print(f"Error printing receipt: {e}")
        else:
            print("Receipt image not found.")


def create_receipt(name, date, amount, amount_fig, invoice_no, pay_for):
    receipt_id = str(uuid.uuid4())
    receipt_data = {
        'ID': receipt_id,
        'Name': name,
        'Date': date,
        'Amount': amount,
        "Amount Fig": amount_fig,
        "Invoice No": invoice_no,
        "Being payed for": pay_for
    }

    # Create receipts directory if it doesn't exist
    if not os.path.exists('receipts'):
        os.makedirs('receipts')

    # Create receipt image
    receipt_template = Image.open('receipt_template.png')
    draw = ImageDraw.Draw(receipt_template)

    # Define font size and style
    font_size = 20
    font = ImageFont.truetype("arial.ttf", font_size)  # Change "arial.ttf" to your desired font file

    # Draw text with specified font
    draw.text((210, 150), f"{receipt_id}", font=font, fill="black")
    draw.text((680, 150), f"{date}", font=font, fill="black")
    draw.text((200, 260), f"{name}", font=font, fill="black")
    draw.text((220, 295), f"{amount}", font=font, fill="black")
    draw.text((250, 380), f"{pay_for}", font=font, fill="black")
    draw.text((220, 410), f"{invoice_no}", font=font, fill="black")
    draw.text((730, 540), f"{amount_fig}", font=font, fill="black")

    receipt_file = f'receipts/{receipt_id}.png'
    receipt_template.save(receipt_file)

    # Record receipt in CSV
    csv_file = 'receipts.csv'
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        df = pd.concat([df, pd.DataFrame([receipt_data])], ignore_index=True)
    else:
        df = pd.DataFrame([receipt_data])
    
    df.to_csv(csv_file, index=False)

    print(f'Receipt created with ID: {receipt_id}')
    return receipt_id  # Return the receipt ID

def print_receipt(receipt_id):
    receipt_image_path = os.path.join("receipts", f"{receipt_id}.png")
    if os.path.exists(receipt_image_path):
        try:
            if sys.platform == "win32":
                # For Windows, use the 'start' command with the 'print' action
                subprocess.run(["start", "/wait", "", "mspaint", "/pt", receipt_image_path], shell=True)
            else:
                print("Printing not supported on this platform.")
        except Exception as e:
            print(f"Error printing receipt: {e}")
    else:
        print("Receipt image not found.")


class LoginScreen(ctk.CTkFrame):
    def __init__(self, master, switch_to_main, **kwargs):
        super().__init__(master, **kwargs)
        self.switch_to_main = switch_to_main

        self.label = ctk.CTkLabel(self, text="Login", font=("Helvetica", 24))
        self.label.pack(pady=12, padx=10)

        self.username_entry = ctk.CTkEntry(self, placeholder_text="Username", width=300, font=("Helvetica", 16))
        self.username_entry.pack(pady=12, padx=10)

        self.password_entry = ctk.CTkEntry(self, placeholder_text="Password", show="*", width=300, font=("Helvetica", 16))
        self.password_entry.pack(pady=12, padx=10)

        self.login_button = ctk.CTkButton(self, text="Login", command=self.login, font=("Helvetica", 16))
        self.login_button.pack(pady=12, padx=10)

        self.login_status = ctk.CTkLabel(self, text="", font=("Helvetica", 16))
        self.login_status.pack(pady=12, padx=10)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if validate_user(username, password):
            self.switch_to_main()
        else:
            self.login_status.configure(text="Invalid username or password")

class MainScreen(ctk.CTkFrame):
    def __init__(self, master, switch_to_receipt_viewer, refresh_receipts, **kwargs):
        super().__init__(master, **kwargs)
        self.switch_to_receipt_viewer = switch_to_receipt_viewer
        self.refresh_receipts = refresh_receipts

        self.label = ctk.CTkLabel(self, text="Main Screen", font=("Helvetica", 24))
        self.label.pack(pady=12, padx=10)

        self.name_entry = ctk.CTkEntry(self, placeholder_text="Name", width=300, font=("Helvetica", 16))
        self.name_entry.pack(pady=12, padx=10)

        self.amount_words_entry = ctk.CTkEntry(self, placeholder_text="Amount in Words", width=300, font=("Helvetica", 16))
        self.amount_words_entry.pack(pady=12, padx=10)

        self.amount_figures_entry = ctk.CTkEntry(self, placeholder_text="Amount in Figures", width=300, font=("Helvetica", 16))
        self.amount_figures_entry.pack(pady=12, padx=10)

        self.description_entry = ctk.CTkEntry(self, placeholder_text="Description", width=300, font=("Helvetica", 16))
        self.description_entry.pack(pady=12, padx=10)

        self.date_entry = ctk.CTkEntry(self, placeholder_text="Date", width=300, font=("Helvetica", 16))
        self.date_entry.pack(pady=12, padx=10)

        self.invoice_number_entry = ctk.CTkEntry(self, placeholder_text="Invoice Number", width=300, font=("Helvetica", 16))
        self.invoice_number_entry.pack(pady=12, padx=10)

        self.create_receipt_button = ctk.CTkButton(self, text="Create Receipt", command=self.create_receipt, font=("Helvetica", 16))
        self.create_receipt_button.pack(pady=12, padx=10)

        self.view_receipts_button = ctk.CTkButton(self, text="View Receipts", command=self.switch_to_receipt_viewer, font=("Helvetica", 16))
        self.view_receipts_button.pack(pady=12, padx=10)

    def create_receipt(self):
        name = self.name_entry.get()
        amount_words = self.amount_words_entry.get()
        amount_figures = self.amount_figures_entry.get()
        description = self.description_entry.get()
        date = self.date_entry.get()
        invoice_number = self.invoice_number_entry.get()

        if not all([name, amount_words, amount_figures, description, date, invoice_number]):
            print("All fields must be filled out.")
            return

        receipt_id = create_receipt(name, date, amount_words, amount_figures, invoice_number, description)
        print(f"Creating receipt for {name}, Amount in Words: {amount_words}, Amount in Figures: {amount_figures}, Description: {description}, Date: {date}, Invoice Number: {invoice_number}")

        self.refresh_receipts()
        self.prompt_print(receipt_id)

    def prompt_print(self, receipt_id):
        layout = ctk.CTkFrame(self)
        label = ctk.CTkLabel(layout, text="Receipt created successfully. Do you want to print it?", font=("Helvetica", 16))
        label.pack(pady=12, padx=10)

        button_layout = ctk.CTkFrame(layout)
        button_layout.pack(pady=12, padx=10)

        yes_button = ctk.CTkButton(button_layout, text="Yes", command=lambda: self.print_and_dismiss(receipt_id, layout), font=("Helvetica", 16))
        no_button = ctk.CTkButton(button_layout, text="No", command=layout.pack_forget, font=("Helvetica", 16))

        yes_button.pack(side="left", padx=5)
        no_button.pack(side="right", padx=5)

        layout.pack(pady=12, padx=10)

    def print_and_dismiss(self, receipt_id, layout):
        self.print_receipt(receipt_id)
        layout.pack_forget()

    def print_receipt(self, receipt_id):
        print_receipt(receipt_id)
        print(f"Printing receipt with ID: {receipt_id}")

class ReceiptManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Receipt Manager")
        self.geometry("800x600")

        self.receipt_viewer_screen = ReceiptViewerScreen(self, switch_to_main=self.show_main_screen)

        self.login_screen = LoginScreen(self, switch_to_main=self.show_main_screen)
        self.main_screen = MainScreen(self, switch_to_receipt_viewer=self.show_receipt_viewer_screen, refresh_receipts=self.receipt_viewer_screen.load_receipts)

        self.current_frame = None
        self.show_login_screen()

    def show_login_screen(self):
        if self.current_frame is not None:
            self.current_frame.pack_forget()
        self.current_frame = self.login_screen
        self.login_screen.pack(fill="both", expand=True)

    def show_main_screen(self):
        if self.current_frame is not None:
            self.current_frame.pack_forget()
        self.current_frame = self.main_screen
        self.main_screen.pack(fill="both", expand=True)

    def show_receipt_viewer_screen(self):
        if self.current_frame is not None:
            self.current_frame.pack_forget()
        self.current_frame = self.receipt_viewer_screen
        self.receipt_viewer_screen.pack(fill="both", expand=True)

if __name__ == '__main__':
    setup_database()
    register_user('admin', 'adminpass')
    app = ReceiptManagerApp()
    app.mainloop()
