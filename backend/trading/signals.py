from django.dispatch import Signal

# Signal sent when an order's status changes (e.g., created, executed, cancelled).
# The sender will be the class that triggered the change, and an 'order' instance will be passed.
order_status_changed = Signal()

# Signal sent when a position is created, updated, or closed.
# The sender will be the class, and 'position' and 'user_id' will be passed.
position_changed = Signal()
