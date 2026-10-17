#!/usr/bin/env python3
"""
Progen Config Builder

Builds and validates a .progen.json for progen
(https://github.com/sivaprasadreddy/progen), and optionally runs progen.

Progen falls back to defaults on invalid values (with only a WARNING), and it
deletes ./<AppName>/ before it generates. This script rejects invalid values
and refuses to run when the target directory already exists.

Usage:
    python3 progen_config.py --app-name shop --base-package com.acme.shop \\
        [--group-id com.acme] [--app-type rest|web|angular] \\
        [--build-tool maven|gradle] [--persistence jpa|jdbc|jooq] \\
        [--db postgresql|mysql|mariadb] [--migration flyway|liquibase] \\
        [--features email,redis,...] [--java 25] [--out-dir DIR] [--run]
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

APP_TYPES = {
    "rest": "REST API",
    "web": "Web App",
    "angular": "Spring Boot + Angular Full Stack",
}
BUILD_TOOLS = {"maven": "Maven", "gradle": "Gradle"}
PERSISTENCE = {"jpa": "Spring Data JPA", "jdbc": "Spring JdbcClient", "jooq": "jOOQ"}
DATABASES = {"postgresql": "PostgreSQL", "mysql": "MySQL", "mariadb": "MariaDB"}
MIGRATIONS = {"flyway": "Flyway", "liquibase": "Liquibase"}
FEATURES = {
    "aws": "SpringCloudAWSSupport",
    "htmx": "HTMXSupport",
    "email": "EmailSupport",
    "rabbitmq": "RabbitMQSupport",
    "redis": "RedisCachingSupport",
    "otel": "OpenTelemetrySupport",
    "k8s": "K8sSupport",
}

APP_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,49}$")
PACKAGE_RE = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$")
JAVA_VERSION_DEFAULT = 25  # progen hard-codes this; --java patches the build file


def fail(message: str, code: int = 1):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def pick(table: dict, value: str, option: str) -> str:
    key = value.strip().lower()
    if key not in table:
        fail(f"{option} '{value}' is invalid. Use one of: {', '.join(table)}")
    return table[key]


def build_config(args) -> dict:
    if not APP_NAME_RE.match(args.app_name):
        fail(f"--app-name '{args.app_name}' is invalid. Use lowercase letters, digits, "
             "and '-', starting with a letter (progen uses it as a directory name).")
    if not PACKAGE_RE.match(args.base_package):
        fail(f"--base-package '{args.base_package}' is not a valid Java package.")
    group_id = args.group_id or args.base_package.rsplit(".", 1)[0]
    if not PACKAGE_RE.match(group_id):
        fail(f"--group-id '{group_id}' is invalid.")
    artifact_id = args.artifact_id or args.app_name
    if not APP_NAME_RE.match(artifact_id):
        fail(f"--artifact-id '{artifact_id}' is invalid.")

    app_type = pick(APP_TYPES, args.app_type, "--app-type")
    features = [f.strip().lower() for f in args.features.split(",") if f.strip()]
    for feature in features:
        if feature not in FEATURES:
            fail(f"--features '{feature}' is invalid. Use any of: {', '.join(FEATURES)}")
    if "htmx" in features and app_type != APP_TYPES["web"]:
        fail("--features htmx needs --app-type web.")

    config = {
        "AppType": app_type,
        "AppName": args.app_name,
        "GroupID": group_id,
        "ArtifactID": artifact_id,
        "AppVersion": args.app_version,
        "BasePackage": args.base_package,
        "BuildTool": pick(BUILD_TOOLS, args.build_tool, "--build-tool"),
        "PersistenceType": pick(PERSISTENCE, args.persistence, "--persistence"),
        "DbType": pick(DATABASES, args.db, "--db"),
        "DbMigrationTool": pick(MIGRATIONS, args.migration, "--migration"),
        # progen sets Thymeleaf from the app type; mirror that here
        "ThymeleafSupport": app_type == APP_TYPES["web"],
    }
    for key, field_name in FEATURES.items():
        config[field_name] = key in features
    return config


def patch_java_version(project_dir: Path, version: int):
    pom = project_dir / "pom.xml"
    gradle = project_dir / "build.gradle"
    if pom.exists():
        text = pom.read_text(encoding="utf-8")
        new = re.sub(r"<java.version>\d+</java.version>",
                     f"<java.version>{version}</java.version>", text, count=1)
        pom.write_text(new, encoding="utf-8")
    elif gradle.exists():
        text = gradle.read_text(encoding="utf-8")
        new = re.sub(r"JavaLanguageVersion\.of\(\d+\)",
                     f"JavaLanguageVersion.of({version})", text, count=1)
        gradle.write_text(new, encoding="utf-8")
    else:
        print("WARNING: no pom.xml or build.gradle found; Java version not changed")
        return
    sdkmanrc = project_dir / ".sdkmanrc"
    if sdkmanrc.exists():
        print(f"NOTE: update .sdkmanrc to a Java {version} distribution "
              "(CI reads the Java version from it)")
    print(f"Set Java version to {version}")


def run_progen(out_dir: Path, config: dict, java_version: int) -> int:
    project_dir = out_dir / config["AppName"]
    if shutil.which("progen") is None:
        fail("progen is not on PATH. Install it: "
             "go install github.com/sivaprasadreddy/progen@latest, "
             "or download a binary from https://github.com/sivaprasadreddy/progen/releases",
             code=3)
    if shutil.which("java") is None:
        print("WARNING: java is not on PATH. progen still generates the files, "
              "but its formatting step (spotless) fails.")

    result = subprocess.run(["progen", "-c", ".progen.json"], cwd=out_dir)
    build_file = project_dir / ("pom.xml" if config["BuildTool"] == "Maven" else "build.gradle")
    if not build_file.exists():
        fail(f"progen did not generate {build_file} (exit code {result.returncode})")
    if result.returncode != 0:
        formatter = "./mvnw spotless:apply" if config["BuildTool"] == "Maven" \
            else "./gradlew spotlessApply"
        print(f"WARNING: progen exited with {result.returncode}, but the project was "
              f"generated. The formatting step probably failed (it needs Java and "
              f"network access). Run '{formatter}' in {project_dir} later.")
    if java_version != JAVA_VERSION_DEFAULT:
        patch_java_version(project_dir, java_version)
    print(f"Project generated at {project_dir}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Build and validate .progen.json")
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--base-package", required=True)
    parser.add_argument("--group-id")
    parser.add_argument("--artifact-id")
    parser.add_argument("--app-version", default="0.0.1-SNAPSHOT")
    parser.add_argument("--app-type", default="rest")
    parser.add_argument("--build-tool", default="maven")
    parser.add_argument("--persistence", default="jpa")
    parser.add_argument("--db", default="postgresql")
    parser.add_argument("--migration", default="flyway")
    parser.add_argument("--features", default="")
    parser.add_argument("--java", type=int, default=JAVA_VERSION_DEFAULT,
                        help="Java version to set after generation (progen uses 25)")
    parser.add_argument("--out-dir", default=".",
                        help="Directory for .progen.json; progen creates <out-dir>/<app-name>/")
    parser.add_argument("--run", action="store_true", help="Run progen after writing the config")
    args = parser.parse_args()

    if args.java < 17:
        fail("--java must be 17 or later (Spring Boot 4 minimum)")
    config = build_config(args)
    out_dir = Path(args.out_dir).resolve()
    if not out_dir.is_dir():
        fail(f"--out-dir '{out_dir}' does not exist")

    project_dir = out_dir / config["AppName"]
    if project_dir.exists():
        # progen deletes this directory before it generates
        fail(f"{project_dir} already exists. progen would delete it. "
             "Choose another --app-name or --out-dir.", code=2)

    config_path = out_dir / ".progen.json"
    if config_path.exists():
        print(f"NOTE: overwriting {config_path}")
    config_path.write_text(json.dumps(config, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {config_path}")
    print(json.dumps(config, indent=1))

    if args.run:
        sys.exit(run_progen(out_dir, config, args.java))


if __name__ == "__main__":
    main()
