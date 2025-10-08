"""Main CLI entry point for buddyctl."""

import typer
from .core.auth import StackSpotAuth, AuthenticationError
from .core.config import BuddyConfig, ConfigurationError
from .cli.agent_validator import AgentValidator, AgentValidationError
from .cli.interactive import InteractiveShell

app = typer.Typer(help="buddyctl - CLI tool for buddy management")
auth_app = typer.Typer(help="Authentication commands")
app.add_typer(auth_app, name="auth")


def initialize_auth() -> StackSpotAuth:
    """Initialize authentication using only system environment variables."""
    auth = StackSpotAuth()

    try:
        # Attempt to get a valid token (will authenticate if needed)
        auth.get_valid_token()
    except AuthenticationError as e:
        typer.echo(f"Authentication failed: {e}", err=True)
        # Continue execution even if auth fails for now

    return auth


@auth_app.command("login")
def auth_login() -> None:
    """Authenticate with StackSpot using environment credentials."""
    auth = StackSpotAuth()

    try:
        # Validate configuration
        auth._validate_config()

        # Attempt to get a valid token
        token = auth.get_valid_token()

        # Get auth status for display
        status = auth.get_auth_status()

        typer.echo("✓ Authentication successful!")
        typer.echo(f"  Realm: {status['realm']}")
        typer.echo(f"  Status: {status['status']}")

    except AuthenticationError as e:
        typer.echo(f"✗ Authentication failed: {e}", err=True)
        raise typer.Exit(1)


@auth_app.command("status")
def auth_status() -> None:
    """Check current authentication status."""
    auth = StackSpotAuth()
    status = auth.get_auth_status()

    if status["authenticated"]:
        typer.echo("✓ " + status["status"])
        typer.echo(f"  Realm: {status['realm']}")
    else:
        typer.echo("✗ " + status["status"])
        if status["realm"]:
            typer.echo(f"  Realm: {status['realm']}")


@auth_app.command("logout")
def auth_logout() -> None:
    """Remove stored authentication credentials."""
    auth = StackSpotAuth()
    auth.logout()
    typer.echo("✓ Successfully logged out")


@app.command("agent-default")
def set_default_agent(agent_id: str) -> None:
    """Set the default agent ID for all StackSpot API requests."""
    config = BuddyConfig()
    auth = StackSpotAuth()
    validator = AgentValidator(auth)

    try:
        # Validate agent ID format and existence
        validator.validate_agent(agent_id, check_existence=False)
        config.set_default_agent_id(agent_id)
        typer.echo(f"✓ Default agent set to: {agent_id}")
    except (ConfigurationError, AgentValidationError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Main entry point for buddyctl CLI."""
    if ctx.invoked_subcommand is None:
        # Start interactive shell
        shell = InteractiveShell()
        shell.run()


if __name__ == "__main__":
    app()
