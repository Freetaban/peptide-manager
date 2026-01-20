"""
Notification Service for Peptide Management System

Provides:
- Windows Toast notifications via plyer
- Scheduled dose reminders
- Low inventory alerts
- Dose overdue warnings

Configuration read from user_preferences table.
"""

import threading
import time
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Callable
from pathlib import Path
import json


class NotificationService:
    """
    Background notification service for treatment reminders.
    
    Features:
    - Morning reminder with day's schedule
    - Individual dose reminders (optional)
    - Overdue dose alerts
    - Low inventory warnings
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._preferences: Dict = {}
        self._callbacks: List[Callable] = []
        
        # Load preferences
        self._load_preferences()
    
    def _get_db(self) -> sqlite3.Connection:
        """Get database connection for current thread."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _load_preferences(self):
        """Load notification preferences from database."""
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT preference_key, preference_value, value_type
                FROM user_preferences
                WHERE category = 'notifications'
            """)
            
            for row in cursor.fetchall():
                key = row['preference_key']
                value = row['preference_value']
                value_type = row['value_type']
                
                # Convert to appropriate type
                if value_type == 'bool':
                    self._preferences[key] = value.lower() == 'true'
                elif value_type == 'int':
                    self._preferences[key] = int(value)
                elif value_type == 'json':
                    self._preferences[key] = json.loads(value)
                else:
                    self._preferences[key] = value
            
            conn.close()
            
        except Exception as ex:
            print(f"⚠️ Error loading notification preferences: {ex}")
            # Use defaults
            self._preferences = {
                'notify_morning_reminder': True,
                'notify_morning_time': '08:00',
                'notify_dose_overdue': True,
                'notify_overdue_hours': 4,
                'notify_low_inventory': True,
                'notify_low_inventory_weeks': 2,
                'notify_method': 'toast',
            }
    
    def get_preference(self, key: str, default=None):
        """Get a preference value."""
        return self._preferences.get(key, default)
    
    def set_preference(self, key: str, value):
        """Update a preference value."""
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            # Determine value_type
            if isinstance(value, bool):
                value_type = 'bool'
                db_value = 'true' if value else 'false'
            elif isinstance(value, int):
                value_type = 'int'
                db_value = str(value)
            elif isinstance(value, (dict, list)):
                value_type = 'json'
                db_value = json.dumps(value)
            else:
                value_type = 'string'
                db_value = str(value)
            
            cursor.execute("""
                UPDATE user_preferences
                SET preference_value = ?, value_type = ?, updated_at = CURRENT_TIMESTAMP
                WHERE preference_key = ?
            """, (db_value, value_type, key))
            
            conn.commit()
            conn.close()
            
            self._preferences[key] = value
            
        except Exception as ex:
            print(f"⚠️ Error saving preference {key}: {ex}")
    
    def send_notification(self, title: str, message: str, timeout: int = 10):
        """
        Send a notification using the configured method.
        
        Args:
            title: Notification title
            message: Notification message
            timeout: Display duration in seconds
        """
        method = self.get_preference('notify_method', 'toast')
        
        if method in ('toast', 'both'):
            self._send_toast(title, message, timeout)
        
        # Call registered callbacks (for GUI integration)
        for callback in self._callbacks:
            try:
                callback(title, message)
            except Exception as ex:
                print(f"⚠️ Notification callback error: {ex}")
    
    def _send_toast(self, title: str, message: str, timeout: int = 10):
        """Send Windows toast notification."""
        try:
            from plyer import notification
            
            notification.notify(
                title=title,
                message=message,
                app_name="Peptide Manager",
                timeout=timeout,
            )
            
        except ImportError:
            print("⚠️ plyer not installed. Install with: pip install plyer")
        except Exception as ex:
            print(f"⚠️ Toast notification error: {ex}")
    
    def register_callback(self, callback: Callable):
        """Register a callback for notifications (for GUI integration)."""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """Unregister a notification callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    # ========== Scheduled Checks ==========
    
    def get_todays_schedule(self) -> List[Dict]:
        """
        Get today's scheduled doses from active cycles.
        
        Returns:
            List of scheduled doses with peptide info
        """
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            today = date.today().isoformat()
            
            # Get active cycles with their schedules
            cursor.execute("""
                SELECT 
                    c.id as cycle_id,
                    c.name as cycle_name,
                    p.name as peptide_name,
                    pr.dose_per_injection_mcg,
                    pr.standard_injection_volume_ml,
                    pp.daily_frequency,
                    pp.five_two_protocol,
                    pp.administration_times,
                    pp.weekday_pattern
                FROM cycles c
                JOIN protocols pr ON c.protocol_id = pr.id
                JOIN peptides p ON pr.peptide_id = p.id
                LEFT JOIN plan_phases pp ON pp.cycle_id = c.id
                WHERE c.status = 'active'
                  AND (c.end_date IS NULL OR c.end_date >= ?)
            """, (today,))
            
            schedule = []
            today_weekday = date.today().isoweekday()
            
            for row in cursor.fetchall():
                # Check if today is a dosing day
                if row['five_two_protocol'] and today_weekday > 5:
                    continue  # Skip weekends for 5/2
                
                weekday_pattern = json.loads(row['weekday_pattern']) if row['weekday_pattern'] else [1,2,3,4,5,6,7]
                if today_weekday not in weekday_pattern:
                    continue
                
                admin_times = json.loads(row['administration_times']) if row['administration_times'] else ['morning']
                daily_freq = row['daily_frequency'] or 1
                
                for timing in admin_times[:daily_freq]:
                    schedule.append({
                        'cycle_id': row['cycle_id'],
                        'cycle_name': row['cycle_name'],
                        'peptide_name': row['peptide_name'],
                        'dose_mcg': row['dose_per_injection_mcg'],
                        'volume_ml': row['standard_injection_volume_ml'],
                        'timing': timing,
                    })
            
            conn.close()
            return schedule
            
        except Exception as ex:
            print(f"⚠️ Error getting schedule: {ex}")
            return []
    
    def check_overdue_doses(self) -> List[Dict]:
        """
        Check for overdue doses.
        
        Returns:
            List of overdue doses
        """
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            overdue_hours = self.get_preference('notify_overdue_hours', 4)
            cutoff = (datetime.now() - timedelta(hours=overdue_hours)).isoformat()
            
            # Get expected doses not yet administered
            # This is a simplified check - in production would need proper scheduling
            cursor.execute("""
                SELECT 
                    c.id as cycle_id,
                    c.name as cycle_name,
                    p.name as peptide_name,
                    MAX(a.administered_at) as last_dose
                FROM cycles c
                JOIN protocols pr ON c.protocol_id = pr.id
                JOIN peptides p ON pr.peptide_id = p.id
                LEFT JOIN administrations a ON a.cycle_id = c.id
                WHERE c.status = 'active'
                GROUP BY c.id
                HAVING last_dose < ? OR last_dose IS NULL
            """, (cutoff,))
            
            overdue = []
            for row in cursor.fetchall():
                overdue.append({
                    'cycle_id': row['cycle_id'],
                    'cycle_name': row['cycle_name'],
                    'peptide_name': row['peptide_name'],
                    'last_dose': row['last_dose'],
                })
            
            conn.close()
            return overdue
            
        except Exception as ex:
            print(f"⚠️ Error checking overdue: {ex}")
            return []
    
    def check_low_inventory(self) -> List[Dict]:
        """
        Check for low inventory items.
        
        Returns:
            List of items with low stock
        """
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            weeks_threshold = self.get_preference('notify_low_inventory_weeks', 2)
            
            # Get peptides with active cycles and check inventory
            cursor.execute("""
                SELECT 
                    p.id,
                    p.name,
                    COALESCE(SUM(prep.volume_remaining_ml), 0) as available_ml,
                    pr.standard_injection_volume_ml * ? * 7 as needed_ml
                FROM peptides p
                JOIN protocols pr ON pr.peptide_id = p.id
                JOIN cycles c ON c.protocol_id = pr.id
                LEFT JOIN preparations prep ON prep.peptide_id = p.id 
                    AND prep.status = 'ready'
                    AND prep.expiry_date >= date('now')
                WHERE c.status = 'active'
                GROUP BY p.id
                HAVING available_ml < needed_ml
            """, (weeks_threshold,))
            
            low_stock = []
            for row in cursor.fetchall():
                low_stock.append({
                    'peptide_id': row['id'],
                    'peptide_name': row['name'],
                    'available_ml': row['available_ml'],
                    'needed_ml': row['needed_ml'],
                    'weeks_supply': row['available_ml'] / (row['needed_ml'] / weeks_threshold) if row['needed_ml'] > 0 else 0,
                })
            
            conn.close()
            return low_stock
            
        except Exception as ex:
            print(f"⚠️ Error checking inventory: {ex}")
            return []
    
    # ========== Background Service ==========
    
    def start(self):
        """Start the background notification service."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("✅ Notification service started")
    
    def stop(self):
        """Stop the background notification service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("🛑 Notification service stopped")
    
    def _run_loop(self):
        """Main service loop."""
        last_morning_check = None
        last_overdue_check = None
        
        while self._running:
            try:
                now = datetime.now()
                
                # Morning reminder check (once per day)
                if self.get_preference('notify_morning_reminder', True):
                    morning_time = self.get_preference('notify_morning_time', '08:00')
                    morning_hour, morning_min = map(int, morning_time.split(':'))
                    
                    if (now.hour == morning_hour and 
                        now.minute >= morning_min and 
                        now.minute < morning_min + 5 and
                        last_morning_check != now.date()):
                        
                        self._send_morning_reminder()
                        last_morning_check = now.date()
                
                # Overdue check (every hour)
                if self.get_preference('notify_dose_overdue', True):
                    if last_overdue_check is None or (now - last_overdue_check).seconds > 3600:
                        overdue = self.check_overdue_doses()
                        if overdue:
                            for dose in overdue[:3]:  # Max 3 alerts
                                self.send_notification(
                                    "⚠️ Dose Mancata",
                                    f"{dose['peptide_name']} - {dose['cycle_name']}"
                                )
                        last_overdue_check = now
                
                # Low inventory check (once per day at 9am)
                if self.get_preference('notify_low_inventory', True):
                    if now.hour == 9 and now.minute < 5:
                        low_stock = self.check_low_inventory()
                        if low_stock:
                            names = ", ".join([s['peptide_name'] for s in low_stock[:3]])
                            self.send_notification(
                                "📦 Scorte Basse",
                                f"Riordina: {names}"
                            )
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except Exception as ex:
                print(f"⚠️ Notification loop error: {ex}")
                time.sleep(60)
    
    def _send_morning_reminder(self):
        """Send morning reminder with today's schedule."""
        schedule = self.get_todays_schedule()
        
        if not schedule:
            return
        
        # Group by timing
        morning_doses = [d for d in schedule if d['timing'] == 'morning']
        evening_doses = [d for d in schedule if d['timing'] == 'evening']
        
        message_parts = []
        if morning_doses:
            names = ", ".join([d['peptide_name'] for d in morning_doses])
            message_parts.append(f"🌅 Mattina: {names}")
        
        if evening_doses:
            names = ", ".join([d['peptide_name'] for d in evening_doses])
            message_parts.append(f"🌙 Sera: {names}")
        
        if message_parts:
            self.send_notification(
                f"📋 Dosi di Oggi ({len(schedule)})",
                "\n".join(message_parts),
                timeout=15
            )


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service(db_path: str = None) -> NotificationService:
    """Get or create the notification service singleton."""
    global _notification_service
    
    if _notification_service is None:
        if db_path is None:
            db_path = "data/production/peptides.db"
        _notification_service = NotificationService(db_path)
    
    return _notification_service


def start_notification_service(db_path: str = None):
    """Start the notification service."""
    service = get_notification_service(db_path)
    service.start()
    return service


def stop_notification_service():
    """Stop the notification service."""
    global _notification_service
    if _notification_service:
        _notification_service.stop()
        _notification_service = None
