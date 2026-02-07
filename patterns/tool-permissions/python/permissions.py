"""
Tool Permissions Pattern - Python Implementation

Risk-based permission system with glob patterns and conditional overrides.
Supports hot-reload configuration.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml


class RiskLevel(IntEnum):
    """Risk levels for tool operations."""
    LOW = 1       # Read-only, no side effects
    MEDIUM = 2    # Reversible changes
    HIGH = 3      # Significant changes, hard to reverse
    CRITICAL = 4  # Destructive or irreversible


@dataclass
class PermissionRule:
    """A single permission rule."""
    pattern: str              # Glob pattern for matching
    risk_level: RiskLevel
    allowed: bool = True
    requires_confirmation: bool = False
    condition: str | None = None  # Expression for conditional rules


@dataclass
class ToolPermissions:
    """Permission configuration for a tool."""
    tool_name: str
    default_risk: RiskLevel = RiskLevel.MEDIUM
    rules: list[PermissionRule] = field(default_factory=list)


class PermissionEvaluator:
    """
    Evaluates permissions based on risk levels and rules.

    Supports:
    - Glob pattern matching for paths/arguments
    - Risk-level-based defaults
    - Conditional overrides with expression evaluation
    - Hot-reload from YAML config
    """

    def __init__(self, max_allowed_risk: RiskLevel = RiskLevel.MEDIUM):
        self.max_allowed_risk = max_allowed_risk
        self.tools: dict[str, ToolPermissions] = {}
        self._config_path: Path | None = None
        self._config_mtime: float = 0

    def load_from_yaml(self, path: str | Path) -> None:
        """Load permission config from YAML file."""
        self._config_path = Path(path)
        self._reload_config()

    def _reload_config(self) -> None:
        """Reload config if file has changed."""
        if not self._config_path or not self._config_path.exists():
            return

        mtime = self._config_path.stat().st_mtime
        if mtime <= self._config_mtime:
            return

        self._config_mtime = mtime

        with open(self._config_path) as f:
            data = yaml.safe_load(f)

        self.tools.clear()
        for tool_name, config in data.get("tools", {}).items():
            rules = []
            for rule_data in config.get("rules", []):
                rules.append(PermissionRule(
                    pattern=rule_data["pattern"],
                    risk_level=RiskLevel[rule_data.get("risk", "MEDIUM").upper()],
                    allowed=rule_data.get("allowed", True),
                    requires_confirmation=rule_data.get("confirm", False),
                    condition=rule_data.get("condition"),
                ))

            self.tools[tool_name] = ToolPermissions(
                tool_name=tool_name,
                default_risk=RiskLevel[config.get("default_risk", "MEDIUM").upper()],
                rules=rules,
            )

    def check_hot_reload(self) -> None:
        """Check for config changes and reload if needed."""
        self._reload_config()

    def evaluate(
        self,
        tool_name: str,
        argument: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, RiskLevel, bool]:
        """
        Evaluate if a tool call is allowed.

        Args:
            tool_name: Name of the tool
            argument: Primary argument (path, command, etc.)
            context: Optional context for condition evaluation

        Returns:
            Tuple of (allowed, risk_level, requires_confirmation)
        """
        self.check_hot_reload()
        context = context or {}

        # Get tool config or use defaults
        tool_config = self.tools.get(tool_name)
        if not tool_config:
            return (True, RiskLevel.MEDIUM, False)

        # Find matching rule
        for rule in tool_config.rules:
            if fnmatch(argument, rule.pattern):
                # Check condition if present
                if rule.condition and not self._eval_condition(rule.condition, context):
                    continue

                allowed = rule.allowed and rule.risk_level <= self.max_allowed_risk
                return (allowed, rule.risk_level, rule.requires_confirmation)

        # No matching rule, use default
        default_risk = tool_config.default_risk
        allowed = default_risk <= self.max_allowed_risk
        return (allowed, default_risk, default_risk >= RiskLevel.HIGH)

    def _eval_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """
        Safely evaluate a condition expression.

        Only supports simple comparisons for security.
        """
        # Very basic expression evaluation
        # In production, use a proper expression parser
        try:
            # Support: "context.key == value" patterns
            if "==" in condition:
                left, right = condition.split("==")
                left = left.strip()
                right = right.strip().strip("'\"")

                # Navigate context path
                value = context
                for part in left.split("."):
                    if part == "context":
                        continue
                    value = value.get(part, None)
                    if value is None:
                        return False

                return str(value) == right
        except Exception:
            pass
        return False


@dataclass
class PermissionResult:
    """Result of a permission check."""
    allowed: bool
    risk_level: RiskLevel
    requires_confirmation: bool
    reason: str | None = None


def check_permission(
    evaluator: PermissionEvaluator,
    tool_name: str,
    argument: str,
    context: dict[str, Any] | None = None,
) -> PermissionResult:
    """Convenience function for permission checking."""
    allowed, risk, confirm = evaluator.evaluate(tool_name, argument, context)

    reason = None
    if not allowed:
        reason = f"Risk level {risk.name} exceeds maximum allowed {evaluator.max_allowed_risk.name}"

    return PermissionResult(
        allowed=allowed,
        risk_level=risk,
        requires_confirmation=confirm,
        reason=reason,
    )


# Example usage
if __name__ == "__main__":
    evaluator = PermissionEvaluator(max_allowed_risk=RiskLevel.MEDIUM)
    evaluator.load_from_yaml("config/tools.yaml")

    # Check various operations
    tests = [
        ("file_read", "/home/user/documents/file.txt"),
        ("file_write", "/etc/passwd"),
        ("bash", "ls -la"),
        ("bash", "rm -rf /"),
    ]

    for tool, arg in tests:
        result = check_permission(evaluator, tool, arg)
        status = "ALLOWED" if result.allowed else "DENIED"
        print(f"{tool}({arg}): {status} (risk: {result.risk_level.name})")
