import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from datetime import datetime

class CustomerManagementSystem:
    """
    Customer/Client Management System for Nexus Tech
    Features:
    - Register new customers and update information
    - Customer categorization (Regular, VIP, Student)
    - Membership level tracking with automatic discounts
    - Loyalty points monitoring
    - Transaction history storage and access
    """
    
    def __init__(self, db_connection):
        self.conn = db_connection
        
    def register_customer(self, name, contact, email, address, customer_type='Regular'):
        """
        Register a new customer in the system
        
        Parameters:
        - name: Customer's full name
        - contact: Phone number
        - email: Email address
        - address: Physical address
        - customer_type: Regular, VIP, or Student (default: Regular)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO Customer_Details 
                (customer_name, customer_contact, customer_email, customer_address, 
                 customer_type, loyalty_points, membership_level, registration_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, contact, email, address, customer_type, 0, 'Bronze', datetime.now()))
            self.conn.commit()
            customer_id = cursor.lastrowid
            return True, customer_id, "Customer registered successfully"
        except Exception as e:
            return False, None, f"Error: {str(e)}"
    
    def update_customer(self, customer_id, name=None, contact=None, email=None, 
                       address=None, customer_type=None):
        """
        Update existing customer information
        
        Parameters:
        - customer_id: ID of customer to update
        - name, contact, email, address, customer_type: Optional fields to update
        """
        try:
            cursor = self.conn.cursor()
            
            # Build dynamic update query
            update_fields = []
            values = []
            
            if name:
                update_fields.append("customer_name = %s")
                values.append(name)
            if contact:
                update_fields.append("customer_contact = %s")
                values.append(contact)
            if email:
                update_fields.append("customer_email = %s")
                values.append(email)
            if address:
                update_fields.append("customer_address = %s")
                values.append(address)
            if customer_type:
                update_fields.append("customer_type = %s")
                values.append(customer_type)
            
            if not update_fields:
                return False, "No fields to update"
            
            values.append(customer_id)
            query = f"UPDATE Customer_Details SET {', '.join(update_fields)} WHERE customer_id = %s"
            
            cursor.execute(query, tuple(values))
            self.conn.commit()
            return True, "Customer updated successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_customer_category(self, customer_id):
        """
        Get customer's current category/type
        Returns: Regular, VIP, or Student
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT customer_type, loyalty_points, membership_level 
                FROM Customer_Details WHERE customer_id = %s
            """, (customer_id,))
            result = cursor.fetchone()
            if result:
                return result[0], result[1], result[2]  # type, points, level
            return None, None, None
        except Exception as e:
            print(f"Error getting customer category: {e}")
            return None, None, None
    
    def update_membership_level(self, customer_id, loyalty_points):
        """
        Update customer's membership level based on loyalty points
        Bronze: 0-499 points
        Silver: 500-999 points
        Gold: 1000-1999 points
        Platinum: 2000+ points
        VIP status applied automatically for Platinum members
        """
        try:
            if loyalty_points < 500:
                level = 'Bronze'
            elif loyalty_points < 1000:
                level = 'Silver'
            elif loyalty_points < 2000:
                level = 'Gold'
            else:
                level = 'Platinum'
            
            cursor = self.conn.cursor()
            
            # Auto-upgrade to VIP if Platinum
            if level == 'Platinum':
                cursor.execute("""
                    UPDATE Customer_Details 
                    SET membership_level = %s, customer_type = 'VIP'
                    WHERE customer_id = %s
                """, (level, customer_id))
            else:
                cursor.execute("""
                    UPDATE Customer_Details 
                    SET membership_level = %s
                    WHERE customer_id = %s
                """, (level, customer_id))
            
            self.conn.commit()
            return True, level
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def calculate_discount(self, customer_id, subtotal):
        """
        Calculate automatic discount based on customer type and membership level
        
        Discount Structure:
        - Student: 10% base discount
        - VIP: 15% base discount
        - Regular: Discount based on membership level
          * Bronze: 0%
          * Silver: 5%
          * Gold: 10%
          * Platinum: 15%
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT customer_type, membership_level, loyalty_points 
                FROM Customer_Details WHERE customer_id = %s
            """, (customer_id,))
            result = cursor.fetchone()
            
            if not result:
                return 0, "Customer not found"
            
            customer_type, membership_level, loyalty_points = result
            discount_percent = 0
            
            # Apply customer type discount
            if customer_type == 'Student':
                discount_percent = 10
            elif customer_type == 'VIP':
                discount_percent = 15
            elif customer_type == 'Regular':
                # Apply membership level discount
                if membership_level == 'Silver':
                    discount_percent = 5
                elif membership_level == 'Gold':
                    discount_percent = 10
                elif membership_level == 'Platinum':
                    discount_percent = 15
            
            # Apply loyalty points discount (100 points = $10 off)
            loyalty_discount = (loyalty_points // 100) * 10
            
            # Calculate total discount
            percentage_discount = subtotal * (discount_percent / 100)
            total_discount = percentage_discount + loyalty_discount
            
            return total_discount, f"{discount_percent}% + ${loyalty_discount} loyalty"
        except Exception as e:
            return 0, f"Error: {str(e)}"
    
    def add_loyalty_points(self, customer_id, purchase_amount):
        """
        Add loyalty points based on purchase amount
        Rule: $1 spent = 1 loyalty point earned
        """
        try:
            points_earned = int(purchase_amount)
            
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE Customer_Details 
                SET loyalty_points = loyalty_points + %s
                WHERE customer_id = %s
            """, (points_earned, customer_id))
            
            # Get updated points
            cursor.execute("SELECT loyalty_points FROM Customer_Details WHERE customer_id = %s", 
                         (customer_id,))
            new_points = cursor.fetchone()[0]
            
            self.conn.commit()
            
            # Update membership level based on new points
            self.update_membership_level(customer_id, new_points)
            
            return True, points_earned, new_points
        except Exception as e:
            return False, 0, f"Error: {str(e)}"
    
    def use_loyalty_points(self, customer_id, points_to_use):
        """
        Deduct loyalty points when used for discount
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT loyalty_points FROM Customer_Details WHERE customer_id = %s", 
                         (customer_id,))
            current_points = cursor.fetchone()[0]
            
            if current_points < points_to_use:
                return False, "Insufficient loyalty points"
            
            cursor.execute("""
                UPDATE Customer_Details 
                SET loyalty_points = loyalty_points - %s
                WHERE customer_id = %s
            """, (points_to_use, customer_id))
            self.conn.commit()
            
            return True, "Points deducted successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def record_transaction(self, customer_id, total_amount, items_purchased, 
                          discount_applied, payment_method):
        """
        Store customer transaction history
        
        Parameters:
        - customer_id: Customer ID
        - total_amount: Total purchase amount
        - items_purchased: String or JSON of items
        - discount_applied: Total discount amount
        - payment_method: Cash, Card, etc.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO Transaction_History 
                (customer_id, transaction_date, total_amount, items_purchased, 
                 discount_applied, payment_method)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (customer_id, datetime.now(), total_amount, items_purchased, 
                  discount_applied, payment_method))
            self.conn.commit()
            
            # Add loyalty points based on purchase
            self.add_loyalty_points(customer_id, total_amount)
            
            return True, "Transaction recorded successfully"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_transaction_history(self, customer_id, limit=10):
        """
        Retrieve customer's transaction history
        
        Parameters:
        - customer_id: Customer ID
        - limit: Number of recent transactions to retrieve (default: 10)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT transaction_id, transaction_date, total_amount, 
                       items_purchased, discount_applied, payment_method
                FROM Transaction_History
                WHERE customer_id = %s
                ORDER BY transaction_date DESC
                LIMIT %s
            """, (customer_id, limit))
            
            transactions = cursor.fetchall()
            return transactions
        except Exception as e:
            print(f"Error retrieving transaction history: {e}")
            return []
    
    def get_customer_analytics(self, customer_id):
        """
        Get comprehensive customer analytics for personalized service
        Returns: Total spent, purchase frequency, favorite categories, etc.
        """
        try:
            cursor = self.conn.cursor()
            
            # Get total spent
            cursor.execute("""
                SELECT COUNT(*), SUM(total_amount), AVG(total_amount)
                FROM Transaction_History
                WHERE customer_id = %s
            """, (customer_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                total_transactions = result[0]
                total_spent = result[1] or 0
                avg_purchase = result[2] or 0
            else:
                total_transactions = 0
                total_spent = 0
                avg_purchase = 0
            
            # Get customer details
            cursor.execute("""
                SELECT customer_name, customer_type, membership_level, 
                       loyalty_points, registration_date
                FROM Customer_Details
                WHERE customer_id = %s
            """, (customer_id,))
            customer_info = cursor.fetchone()
            
            return {
                'customer_name': customer_info[0] if customer_info else 'N/A',
                'customer_type': customer_info[1] if customer_info else 'N/A',
                'membership_level': customer_info[2] if customer_info else 'N/A',
                'loyalty_points': customer_info[3] if customer_info else 0,
                'registration_date': customer_info[4] if customer_info else None,
                'total_transactions': total_transactions,
                'total_spent': float(total_spent),
                'average_purchase': float(avg_purchase)
            }
        except Exception as e:
            print(f"Error getting customer analytics: {e}")
            return None
    
    def get_vip_customers(self):
        """
        Get list of all VIP customers (high loyalty points)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT customer_id, customer_name, customer_contact, 
                       loyalty_points, membership_level
                FROM Customer_Details
                WHERE customer_type = 'VIP' OR membership_level = 'Platinum'
                ORDER BY loyalty_points DESC
            """)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting VIP customers: {e}")
            return []
    
    def search_customers(self, search_term):
        """
        Search customers by name, contact, or email
        """
        try:
            cursor = self.conn.cursor()
            search_pattern = f"%{search_term}%"
            cursor.execute("""
                SELECT customer_id, customer_name, customer_contact, 
                       customer_email, customer_type, loyalty_points
                FROM Customer_Details
                WHERE customer_name LIKE %s 
                   OR customer_contact LIKE %s 
                   OR customer_email LIKE %s
            """, (search_pattern, search_pattern, search_pattern))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error searching customers: {e}")
            return []


# SQL Schema for Customer Management
"""
-- Enhanced Customer Details Table
CREATE TABLE IF NOT EXISTS Customer_Details (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_name VARCHAR(100) NOT NULL,
    customer_contact VARCHAR(20),
    customer_email VARCHAR(100),
    customer_address TEXT,
    customer_type ENUM('Regular', 'VIP', 'Student') DEFAULT 'Regular',
    membership_level ENUM('Bronze', 'Silver', 'Gold', 'Platinum') DEFAULT 'Bronze',
    loyalty_points INT DEFAULT 0,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_purchase_date DATETIME,
    INDEX idx_customer_type (customer_type),
    INDEX idx_membership_level (membership_level)
);

-- Transaction History Table
CREATE TABLE IF NOT EXISTS Transaction_History (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10,2) NOT NULL,
    items_purchased TEXT,
    discount_applied DECIMAL(10,2) DEFAULT 0,
    payment_method VARCHAR(50),
    FOREIGN KEY (customer_id) REFERENCES Customer_Details(customer_id) ON DELETE CASCADE,
    INDEX idx_customer_date (customer_id, transaction_date)
);
"""

# Example Usage
if __name__ == "__main__":
    # Example connection (replace with actual credentials)
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='your_password',
            database='nexus_tech'
        )
        
        cms = CustomerManagementSystem(conn)
        
        # Example 1: Register new customer
        success, cust_id, msg = cms.register_customer(
            name="John Doe",
            contact="555-0123",
            email="john@example.com",
            address="123 Main St, City",
            customer_type="Student"
        )
        print(f"Registration: {msg}")
        
        # Example 2: Calculate discount
        discount, desc = cms.calculate_discount(cust_id, 100.00)
        print(f"Discount: ${discount} ({desc})")
        
        # Example 3: Record transaction
        success, msg = cms.record_transaction(
            customer_id=cust_id,
            total_amount=100.00,
            items_purchased="Laptop, Mouse",
            discount_applied=discount,
            payment_method="Card"
        )
        print(f"Transaction: {msg}")
        
        # Example 4: Get customer analytics
        analytics = cms.get_customer_analytics(cust_id)
        if analytics:
            print(f"Analytics: {analytics}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
