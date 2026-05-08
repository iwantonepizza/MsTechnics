BOX_TO_STATUSES = {
    "received":            ["sent_to_control"],
    "at_work":             ["apply_in_control", "sent_to_service", "work_in_service"],
    "complete":            ["done", "unable"],
    "archive":             ["archive_done", "archive_unable"],
    "application_history": ["done", "unable", "archive_done", "archive_unable"],
    "unable":              ["unable", "archive_unable"],
    "all":                 None,
}


def apply_box_filter(qs, box: str):
    if box == "all":
        return qs
    statuses = BOX_TO_STATUSES.get(box)
    if statuses is None:
        return qs.none()
    return qs.filter(status__name__in=statuses)
