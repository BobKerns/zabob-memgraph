#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "click>=8.3.1",
# ]
# ///
"""
Docker build script for zabob-memgraph using base images.

This script builds Docker images using pre-built base images from GHCR.
It's much simpler than the old shell script because heavy dependencies
are already baked into base images.
"""

import subprocess
import sys

import click


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    click.echo(f"→ {' '.join(cmd)}", err=True)
    result = subprocess.run(cmd, check=False)
    if check and result.returncode != 0:
        click.echo(f"✗ Command failed with exit code {result.returncode}", err=True)
        sys.exit(result.returncode)
    return result


@click.group()
def cli():
    """Build zabob-memgraph Docker images using pre-built base images."""
    pass


@cli.command()
@click.option(
    "--registry",
    default="ghcr.io",
    help="Container registry",
    show_default=True,
)
@click.option(
    "--image-name",
    default="bobkerns/zabob-memgraph",
    help="Image name",
    show_default=True,
)
@click.option(
    "--base-version",
    default="v4",
    help="Base image version to use",
    show_default=True,
)
@click.option(
    "--tag",
    default="latest",
    help="Tag for the built image",
    show_default=True,
)
@click.option(
    "--push",
    is_flag=True,
    help="Push the image after building",
)
def test(
    registry: str,
    image_name: str,
    base_version: str,
    tag: str,
    push: bool,
):
    """Build the test image (amd64 only)."""
    click.echo("🔨 Building test image...")
    click.echo(f"   Base: {registry}/{image_name}/base-test:{base_version}")
    click.echo(f"   Tag:  {image_name}:test-{tag}")
    click.echo()

    build_args = [
        f"BASE_IMAGE_REGISTRY={registry}",
        f"BASE_IMAGE_NAME={image_name}",
        f"BASE_IMAGE_VERSION={base_version}",
    ]

    cmd = [
        "docker", "build",
        "-f", "Dockerfile.test",
        "-t", f"{image_name}:test-{tag}",
    ]

    for arg in build_args:
        cmd.extend(["--build-arg", arg])

    cmd.append(".")

    run_command(cmd)

    click.echo(f"✓ Test image built: {image_name}:test-{tag}", err=True)

    if push:
        click.echo(f"📤 Pushing {image_name}:test-{tag}...", err=True)
        run_command(["docker", "push", f"{image_name}:test-{tag}"])
        click.echo(f"✓ Pushed {image_name}:test-{tag}", err=True)


@cli.command()
@click.option(
    "--registry",
    default="ghcr.io",
    help="Container registry",
    show_default=True,
)
@click.option(
    "--image-name",
    default="bobkerns/zabob-memgraph",
    help="Image name",
    show_default=True,
)
@click.option(
    "--base-version",
    default="v4",
    help="Base image version to use",
    show_default=True,
)
@click.option(
    "--tag",
    default="latest",
    help="Tag for the built image",
    show_default=True,
)
@click.option(
    "--platform",
    default=None,
    help="Platform to build for (e.g., linux/amd64, linux/arm64)",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push the image after building",
)
def runtime(
    registry: str,
    image_name: str,
    base_version: str,
    tag: str,
    platform: str | None,
    push: bool,
):
    """Build the runtime image (multi-arch capable)."""
    click.echo("🔨 Building runtime image...")
    click.echo(f"   Base: {registry}/{image_name}/base-deps:{base_version}")
    click.echo(f"   Tag:  {image_name}:{tag}")
    if platform:
        click.echo(f"   Platform: {platform}")
    click.echo()

    build_args = [
        f"BASE_IMAGE_REGISTRY={registry}",
        f"BASE_IMAGE_NAME={image_name}",
        f"BASE_IMAGE_VERSION={base_version}",
    ]

    cmd = [
        "docker", "build",
        "-f", "Dockerfile",
        "-t", f"{image_name}:{tag}",
    ]

    if platform:
        cmd.extend(["--platform", platform])

    for arg in build_args:
        cmd.extend(["--build-arg", arg])

    cmd.append(".")

    run_command(cmd)

    click.echo(f"✓ Runtime image built: {image_name}:{tag}", err=True)

    if push:
        click.echo(f"📤 Pushing {image_name}:{tag}...", err=True)
        run_command(["docker", "push", f"{image_name}:{tag}"])
        click.echo(f"✓ Pushed {image_name}:{tag}", err=True)


@cli.command()
@click.option(
    "--registry",
    default="ghcr.io",
    help="Container registry",
    show_default=True,
)
@click.option(
    "--image-name",
    default="bobkerns/zabob-memgraph",
    help="Image name",
    show_default=True,
)
@click.option(
    "--version",
    default="v4",
    help="Version tag for base images",
    show_default=True,
)
@click.option(
    "--push",
    is_flag=True,
    help="Push images after building",
)
@click.option(
    "--platform",
    default="linux/amd64",
    help="Platform to build for",
    show_default=True,
)
def base(
    registry: str,
    image_name: str,
    version: str,
    push: bool,
    platform: str,
):
    """Build base images (base-deps, base-playwright, base-test)."""
    click.echo("🔨 Building base images...")
    click.echo(f"   Version: {version}")
    click.echo(f"   Platform: {platform}")
    click.echo()

    # Build base-deps
    click.echo("📦 Building base-deps...", err=True)
    base_deps_tag = f"{registry}/{image_name}/base-deps:{version}"
    cmd = [
        "docker", "build",
        "-f", "Dockerfile.base-deps",
        "--platform", platform,
        "-t", base_deps_tag,
        ".",
    ]
    run_command(cmd)
    click.echo(f"✓ Built {base_deps_tag}", err=True)

    if push:
        run_command(["docker", "push", base_deps_tag])
        click.echo(f"✓ Pushed {base_deps_tag}", err=True)

    # Only build playwright and test for amd64
    if "amd64" not in platform:
        click.echo("⚠ Skipping base-playwright and base-test (amd64 only)",
                   err=True)
        return

    # Build base-playwright using Dockerfile.base-playwright
    click.echo("\n📦 Building base-playwright...", err=True)
    base_playwright_tag = f"{registry}/{image_name}/base-playwright:{version}"

    build_args = [
        f"BASE_IMAGE_REGISTRY={registry}",
        f"BASE_IMAGE_NAME={image_name}",
        f"BASE_IMAGE_VERSION={version}",
    ]

    cmd = [
        "docker", "build",
        "-f", "Dockerfile.base-playwright",
        "--platform", platform,
        "-t", base_playwright_tag,
    ]

    for arg in build_args:
        cmd.extend(["--build-arg", arg])

    cmd.append(".")

    run_command(cmd)
    click.echo(f"✓ Built {base_playwright_tag}", err=True)

    if push:
        run_command(["docker", "push", base_playwright_tag])
        click.echo(f"✓ Pushed {base_playwright_tag}", err=True)

    # Build base-test using Dockerfile.base-test
    click.echo("\n📦 Building base-test...", err=True)
    base_test_tag = f"{registry}/{image_name}/base-test:{version}"

    cmd = [
        "docker", "build",
        "-f", "Dockerfile.base-test",
        "--platform", platform,
        "-t", base_test_tag,
    ]

    for arg in build_args:
        cmd.extend(["--build-arg", arg])

    cmd.append(".")

    run_command(cmd)
    click.echo(f"✓ Built {base_test_tag}", err=True)

    if push:
        run_command(["docker", "push", base_test_tag])
        click.echo(f"✓ Pushed {base_test_tag}", err=True)

    click.echo("\n✅ All base images built successfully!", err=True)


@cli.command()
@click.option(
    "--image-name",
    default="bobkerns/zabob-memgraph",
    help="Image name",
    show_default=True,
)
@click.option(
    "--tag",
    default="test-latest",
    help="Tag of test image to run",
    show_default=True,
)
def run_tests(image_name: str, tag: str):
    """Run tests in the test image."""
    click.echo(f"🧪 Running tests in {image_name}:{tag}...", err=True)
    cmd = ["docker", "run", "--rm", f"{image_name}:{tag}"]
    run_command(cmd)
    click.echo("✓ Tests passed!", err=True)


if __name__ == "__main__":
    cli()
