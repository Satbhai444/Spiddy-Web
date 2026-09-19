"""
SpiddyWeb — Application-wide constants.

Centralised configuration values used across views, forms, and utilities.
"""

# ── File Upload Limits ────────────────────────────────────────────────────────
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024          # 2 GB per file
MAX_UPLOADS_PER_HOUR = 10                        # max uploads per IP per hour
MAX_UPLOAD_BYTES_PER_HOUR = 5 * 1024 * 1024 * 1024  # 5 GB per IP per hour

# ── PIN Security ──────────────────────────────────────────────────────────────
MAX_PIN_ATTEMPTS = 5
PIN_LOCKOUT_SECONDS = 900                        # 15 minutes

# ── Contact Form ──────────────────────────────────────────────────────────────
MAX_CONTACT_PER_HOUR = 3

# ── Blocked Extensions ────────────────────────────────────────────────────────
BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.sh', '.msi', '.com', '.scr', '.pif',
    '.vbs', '.vbe', '.wsf', '.wsh', '.ps1', '.ps2', '.reg', '.dll',
    '.sys', '.drv', '.hta', '.jar',
}

# ── Preview Types ─────────────────────────────────────────────────────────────
PREVIEW_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
PREVIEW_VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.ogg'}
PREVIEW_AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}
PREVIEW_TEXT_EXTS = {'.txt', '.py', '.js', '.json', '.css', '.html', '.md', '.csv', '.log'}

# ── Room Reactions ────────────────────────────────────────────────────────────
ALLOWED_REACTION_EMOJIS = {'🕸️', '🕷️', '❤️', '🔥', '😂', '⚡'}
