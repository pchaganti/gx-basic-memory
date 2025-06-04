"""Migration status prompt for Basic Memory MCP server."""

from typing import Optional

from basic_memory.mcp.server import mcp


@mcp.prompt(
    description="""Get migration status with recommendations for AI assistants.
    
    This prompt provides both current migration status and guidance on how
    AI assistants should respond when migration is in progress or completed.
    """,
)
async def migration_status_prompt(
) -> str:
    """Get migration status with AI assistant guidance.

    This prompt provides detailed migration status information along with
    recommendations for how AI assistants should handle different migration states.

    Returns:
        Formatted migration status with AI assistant guidance
    """
    try:
        from basic_memory.services.migration_service import migration_manager

        state = migration_manager.state

        # Build status report
        lines = [
            "# Basic Memory Migration Status",
            "",
            f"**Current Status**: {state.status.value.replace('_', ' ').title()}",
            f"**System Ready**: {'Yes' if migration_manager.is_ready else 'No'}",
            "",
        ]

        if migration_manager.is_ready:
            lines.extend(
                [
                    "✅ **All migrations completed** - System is fully operational",
                    "",
                    "All Basic Memory MCP tools are available and functioning normally.",
                    "You can proceed with any knowledge management tasks.",
                ]
            )
        else:
            lines.append(f"**Status Message**: {state.message}")

            if state.status.value == "in_progress":
                if state.projects_total > 0:
                    progress = f" ({state.projects_migrated}/{state.projects_total})"
                    lines.append(f"**Progress**: {progress}")

                lines.extend(
                    [
                        "",
                        "🔄 **Migration in progress** - Legacy data is being migrated to new format",
                        "",
                        "**Impact**: Some tools may show status messages instead of normal responses",
                        "until migration completes (usually 1-3 minutes).",
                    ]
                )

            elif state.status.value == "failed":
                lines.extend(
                    [
                        "",
                        f"❌ **Migration failed**: {state.error or 'Unknown error'}",
                        "",
                        "**Impact**: System may have limited functionality until issue is resolved.",
                    ]
                )

        # Convert string parameter to boolean
        include_recs = True

        if include_recs and not migration_manager.is_ready:
            lines.extend(
                [
                    "",
                    "---",
                    "",
                    "## AI Assistant Recommendations",
                    "",
                    "**When migration is in progress:**",
                    "- Inform the user about the background migration",
                    "- Suggest using `migration_status()` tool to check progress",
                    "- Explain that most tools will work normally once migration completes",
                    "- Avoid creating complex workflows until migration is done",
                    "",
                    "**What to tell users:**",
                    "- 'Basic Memory is upgrading your knowledge base in the background'",
                    "- 'This usually takes 1-3 minutes depending on your data size'",
                    "- 'You can check progress anytime with the migration_status tool'",
                    "- 'Most functionality will be available once the upgrade completes'",
                ]
            )

        return "\n".join(lines)

    except Exception as e:
        return f"""# Migration Status - Error

❌ **Unable to check migration status**: {str(e)}

## AI Assistant Recommendations

**When status is unavailable:**
- Assume the system is likely working normally
- Try proceeding with normal operations
- If users report issues, suggest checking logs or restarting
"""
