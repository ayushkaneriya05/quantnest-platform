from django.db import migrations


RETIRED_APPS = ("marketplace", "community", "gamification", "learning", "reputation", "platform_events")
TABLES = (
    "learning_path", "learning_course_prerequisites", "learning_course", "learning_course_module",
    "learning_lesson", "learning_lesson_resource", "learning_course_enrollment", "learning_lesson_progress",
    "learning_quiz", "learning_quiz_question", "learning_quiz_attempt", "learning_assignment",
    "learning_assignment_submission", "learning_certificate", "learning_user_signal", "learning_recommendation",
    "reputation_trader_profile", "reputation_score", "reputation_trading_proof", "reputation_backtest_proof",
    "reputation_strategy_verification", "reputation_trade_replay", "reputation_ai_moderation_flag",
    "reputation_mentor_profile", "reputation_office_hour_session", "reputation_mentorship_booking",
    "marketplace_listing", "marketplace_subscription", "strategy_review", "creator_earning",
    "gamification_xp_grant_limit", "gamification_xp_event", "gamification_user_xp_balance",
    "gamification_achievement", "gamification_user_achievement", "gamification_streak",
    "gamification_challenge", "gamification_challenge_participant", "gamification_leaderboard_snapshot",
    "gamification_user_trust_flag", "gamification_anti_gaming_rule", "community_profile", "community_topic",
    "community_strategy_room", "community_post", "community_post_attachment", "community_comment",
    "community_reaction", "community_bookmark", "community_follow", "community_post_report",
    "community_moderation_action", "platform_domain_event", "platform_activity_event",
)


def remove_retired_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing = set(connection.introspection.table_names())
    tables = [name for name in TABLES if name in existing]
    if tables and connection.vendor == "postgresql":
        # Drop the whole retired set together. RESTRICT protects unexpected external dependencies.
        schema_editor.execute("DROP TABLE " + ", ".join(schema_editor.quote_name(name) for name in tables))
    elif tables:
        with connection.constraint_checks_disabled():
            for name in reversed(tables):
                schema_editor.execute("DROP TABLE " + schema_editor.quote_name(name))
    apps.get_model("contenttypes", "ContentType").objects.filter(app_label__in=RETIRED_APPS).delete()


class Migration(migrations.Migration):
    atomic = False
    dependencies = [("common", "0005_alter_exchangeconfig_timezone"),
                    ("contenttypes", "0002_remove_content_type_name"),
                    ("trade_journal", "0002_execution_reviews")]
    operations = [migrations.RunPython(remove_retired_tables)]
