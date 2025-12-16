from apscheduler.schedulers.background import BackgroundScheduler

from utils.database.database import get_db_manager
from utils.auth.jwt_utils import init_jwt_manager
from utils.auth.jwt_utils import get_jwt_manager


def initialize_app(app=None):
    """Initialize JWT manager and schedule token cleanup."""
    db = get_db_manager()
    init_jwt_manager(db)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: get_jwt_manager().cleanup_expired_tokens(),
        "interval",
        hours=1
    )

    scheduler.start()
