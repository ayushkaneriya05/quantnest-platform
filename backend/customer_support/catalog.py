"""Customer-facing request labels, shared with both frontend enquiry forms."""
REQUEST_TYPES = [
    ('general', 'General enquiry'), ('custom', 'Custom development'),
    ('private', 'Private deployment'), ('support', 'Product support'),
    ('feedback', 'Feedback or suggestion'), ('grievance', 'Grievance'),
    ('security', 'Security report'),
]

TICKET_STATUS_LABELS = {
    'received': 'Received',
    'awaiting_support': 'Awaiting support',
    'awaiting_customer': 'Awaiting your reply',
    'in_progress': 'In progress',
    'resolved': 'Resolved',
    'closed': 'Closed',
}


def get_support_specification():
    return {
        'request_types': [{'value': value, 'label': label} for value, label in REQUEST_TYPES],
        'ticket_status_labels': TICKET_STATUS_LABELS,
    }
