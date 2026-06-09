def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.
    Example: 107.3 -> "1min 47s"
    Example: 5.2 -> "5.2s"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    
    if remaining_seconds == 0:
        return f"{minutes}min"
    
    return f"{minutes}min {remaining_seconds}s"
