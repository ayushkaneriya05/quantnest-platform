from datetime import date, datetime
from decimal import Decimal

from django.forms.models import model_to_dict
from django.utils import timezone

from strategies.models import Strategy

from .models import AuditLog, ComplianceCheck, StrategyApproval


class AuditService:
    @staticmethod
    def _json_safe(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {
                str(item_key): AuditService._json_safe(item_value)
                for item_key, item_value in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [AuditService._json_safe(item) for item in value]
        return str(value)

    @staticmethod
    def log_action(user, action, entity, old_value=None, new_value=None, request=None):
        return AuditLog.objects.create(
            user=user,
            action=action,
            entity_type=entity.__class__.__name__,
            entity_id=str(entity.pk or ""),
            entity_name=str(entity),
            old_value=AuditService._json_safe(old_value or {}),
            new_value=AuditService._json_safe(new_value or {}),
            ip_address=(request.META.get("REMOTE_ADDR") if request else None),
            user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else ""),
            session_id=(request.session.session_key if request and request.session else ""),
        )

    @staticmethod
    def request_strategy_approval(strategy, user, comments=""):
        approval, _ = StrategyApproval.objects.update_or_create(
            strategy=strategy,
            status="PENDING",
            defaults={"requested_by": user, "comments": comments},
        )
        Strategy.objects.filter(id=strategy.id).update(visibility="PUBLIC")
        AuditService.log_action(user, "CREATE", approval, new_value={"action": "Approval requested", "strategy": strategy.name})
        return approval

    @staticmethod
    def decide_approval(approval, approver, status_value, comments=""):
        old_status = approval.status
        approval.status = status_value
        approval.approved_by = approver
        approval.comments = comments or approval.comments
        approval.decided_at = timezone.now()
        approval.save(update_fields=["status", "approved_by", "comments", "decided_at", "updated_at"])
        strategy = approval.strategy
        if status_value == "APPROVED":
            strategy.visibility = "MARKETPLACE"
        elif status_value == "REJECTED" and strategy.visibility == "MARKETPLACE":
            strategy.visibility = "PRIVATE"
        strategy.save(update_fields=["visibility", "updated_at"])
        AuditService.log_action(
            approver,
            "APPROVE" if status_value == "APPROVED" else "REJECT",
            approval,
            old_value={"status": old_status},
            new_value={"status": status_value, "strategy": strategy.name},
        )
        return approval

    @staticmethod
    def run_compliance_checks(strategy):
        """Run a comprehensive compliance suite against a strategy."""
        # Clear previous checks for this strategy
        ComplianceCheck.objects.filter(strategy=strategy).delete()

        checks = []

        # 1. Must have at least one instrument in watchlist
        has_watchlist = strategy.watchlist_instruments.exists()
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="HAS_WATCHLIST",
            passed=has_watchlist,
            details={"message": "Strategy must have at least one instrument in the watchlist"},
        ))

        # 2. Must have active rule groups
        has_rules = strategy.rule_groups.filter(is_active=True).exists()
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="HAS_RULES",
            passed=has_rules,
            details={"message": "Strategy must have at least one active rule group"},
        ))

        # 3. Must have position sizing configured
        has_position_sizing = hasattr(strategy, "position_sizing_rule")
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="RISK_CONFIGURED",
            passed=has_position_sizing,
            details={"message": "Strategy must have a position sizing rule"},
        ))

        # 4. Must have entry rules
        has_entry_rules = strategy.rule_groups.filter(type="ENTRY", is_active=True).exists()
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="HAS_ENTRY_RULES",
            passed=has_entry_rules,
            details={"message": "Strategy must have at least one active entry rule group"},
        ))

        # 5. Must have exit rules (stop loss or target)
        has_exit_rules = strategy.rule_groups.filter(type__in=["STOP_LOSS", "TARGET"], is_active=True).exists()
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="HAS_EXIT_RULES",
            passed=has_exit_rules,
            details={"message": "Strategy must have at least one active exit rule (SL or target)"},
        ))

        # 6. Must have time rules configured
        has_time_rules = hasattr(strategy, "time_rule")
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="HAS_TIME_RULES",
            passed=has_time_rules,
            details={"message": "Strategy should have time rules configured for session management"},
        ))

        # 7. Must have an entry order config
        has_entry_config = hasattr(strategy, "entry_order_config")
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="HAS_ENTRY_CONFIG",
            passed=has_entry_config,
            details={"message": "Strategy must have entry order configuration"},
        ))

        # 8. Check for at least one successful backtest
        has_backtest = strategy.backtest_runs.filter(status="COMPLETED").exists()
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="HAS_BACKTEST",
            passed=has_backtest,
            details={"message": "Strategy should have at least one completed backtest before marketplace listing"},
        ))

        # 9. Strategy must not be in DRAFT status
        is_active = strategy.status != "DRAFT"
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="NOT_DRAFT",
            passed=is_active,
            details={"message": "Strategy must be activated (not in DRAFT status) before approval"},
        ))

        # 10. Naming convention — name length check
        name_ok = len(strategy.name.strip()) >= 5
        checks.append(ComplianceCheck.objects.create(
            strategy=strategy,
            check_type="NAME_LENGTH",
            passed=name_ok,
            details={"message": "Strategy name must be at least 5 characters"},
        ))

        return checks

    @staticmethod
    def get_compliance_summary(strategy):
        """Return a summary dict of the latest compliance checks for a strategy."""
        checks = ComplianceCheck.objects.filter(strategy=strategy).order_by("-checked_at")
        total = checks.count()
        passed = checks.filter(passed=True).count()
        failed = total - passed
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "score": round((passed / total) * 100, 1) if total > 0 else 0,
            "last_checked": checks.first().checked_at.isoformat() if checks.exists() else None,
        }

    @staticmethod
    def snapshot_instance(instance):
        try:
            return AuditService._json_safe(model_to_dict(instance))
        except Exception:
            return AuditService._json_safe({"id": getattr(instance, "pk", None), "repr": str(instance)})
