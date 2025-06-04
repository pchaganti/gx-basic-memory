"""Migration status tool for Basic Memory MCP server."""

from typing import Optional

from loguru import logger

from basic_memory.mcp.server import mcp
from basic_memory.mcp.project_session import get_active_project


@mcp.tool(
    description="""Check the status of system migration and background operations.
    
    Use this tool to:
    - Check if migration is in progress or completed
    - Get detailed migration progress information
    - Understand if the system is ready for normal operations
    - Get specific error details if migration failed
    """,
)
async def migration_status(project: Optional[str] = None) -> str:
    """Get current migration status and system readiness information.

    This tool provides detailed information about any ongoing or completed
    migration operations, helping users understand system availability.

    Args:
        project: Optional project name (included for consistency with other tools)

    Returns:
        Detailed migration status including:
        - Current migration state (ready, in progress, failed, etc.)
        - Progress information if migration is running
        - Error details if migration failed
        - Estimated completion information
        - Guidance on next steps

    Examples:
        # Check current migration status
        migration_status()

        # Get migration status for specific project context
        migration_status(project="work-project")
    """
    logger.info("MCP tool call tool=migration_status")

    try:
        from basic_memory.services.migration_service import migration_manager

        # Get current migration state
        state = migration_manager.state

        # Build detailed status response
        status_lines = [
            "# Migration Status",
            "",
            f"**Current Status**: {state.status.value.replace('_', ' ').title()}",
            "",
        ]

        if migration_manager.is_ready:
            status_lines.extend(
                [
                    "✅ **System Ready**: All migrations completed successfully",
                    "",
                    "The system is fully operational and ready for normal use. All MCP tools",
                    "are available and functioning normally.",
                ]
            )
        else:
            # Migration in progress or failed
            status_lines.append(f"**Message**: {state.message}")

            if state.status.value == "in_progress":
                status_lines.extend(
                    [
                        "",
                        "🔄 **Migration in Progress**",
                        "",
                    ]
                )

                if state.projects_total > 0:
                    progress_pct = (state.projects_migrated / state.projects_total) * 100
                    status_lines.extend(
                        [
                            f"- **Progress**: {state.projects_migrated}/{state.projects_total} projects ({progress_pct:.0f}%)",
                            f"- **Remaining**: {state.projects_total - state.projects_migrated} projects",
                        ]
                    )

                status_lines.extend(
                    [
                        "",
                        "**What's happening**: Basic Memory is migrating legacy project data",
                        "to the new unified database format. This process runs in the background",
                        "and most tools will show status messages until completion.",
                        "",
                        "**Estimated time**: Usually 1-3 minutes depending on knowledge base size",
                        "",
                        "**What you can do**: Wait for migration to complete, or check status",
                        "again in a few moments. The system will be fully operational once finished.",
                    ]
                )

            elif state.status.value == "failed":
                status_lines.extend(
                    [
                        "",
                        "❌ **Migration Failed**",
                        "",
                        f"**Error**: {state.error or 'Unknown error occurred'}",
                        "",
                        "**What this means**: The automatic migration encountered an issue.",
                        "Basic Memory may still work, but some legacy data might not be available.",
                        "",
                        "**Recommended actions**:",
                        "1. Try running `basic-memory sync` manually from the command line",
                        "2. Check the logs for more detailed error information",
                        "3. If issues persist, consider filing a support issue",
                    ]
                )

            elif state.status.value == "pending":
                status_lines.extend(
                    [
                        "",
                        "⏳ **Migration Pending**",
                        "",
                        "Migration has been detected as needed but hasn't started yet.",
                        "This usually resolves automatically within a few seconds.",
                    ]
                )

        # Add project context if provided
        if project:
            try:
                active_project = get_active_project(project)
                status_lines.extend(
                    [
                        "",
                        "---",
                        "",
                        f"**Active Project**: {active_project.name}",
                        f"**Project Path**: {active_project.path}",
                    ]
                )
            except Exception as e:
                logger.debug(f"Could not get project info: {e}")
                # Don't fail the tool for project info issues

        return "\n".join(status_lines)

    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return f"""# Migration Status - Error

❌ **Unable to check migration status**

**Error**: {str(e)}

**What this means**: There was a technical issue checking the migration status.
The system is likely functioning normally, but status information is unavailable.

**Recommended action**: Try again in a moment, or proceed with normal operations.
"""
