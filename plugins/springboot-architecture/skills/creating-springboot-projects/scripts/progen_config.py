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
        [--features email,redis,...] [--java 25] [--out-dir DIR] [--run] \\
        [--ignore-jdk-check]
"""

import argparse
import json
import os
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
# Reserved keywords and literals cannot be package segments
JAVA_RESERVED = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "true", "false", "null", "_",
}
# progen prints this when only its final spotless step fails
FORMAT_FAILURE_MARKER = "failed to format project code"
JAVA_VERSION_DEFAULT = 25  # progen hard-codes this; --java patches the build file
# progen's formatting step runs palantir-java-format, which fails on newer JDKs
# (JDK 27 with every version up to 2.102.0, checked 2026-10-21). The step also
# removes an unused import of a class Spring Security 7 dropped, so when it fails
# the project doesn't compile.
FORMATTER_MAX_JDK = 25


def fail(message: str, code: int = 1):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def pick(table: dict, value: str, option: str) -> str:
    key = value.strip().lower()
    if key not in table:
        fail(f"{option} '{value}' is invalid. Use one of: {', '.join(table)}")
    return table[key]


def is_java_package(name: str) -> bool:
    return bool(PACKAGE_RE.match(name)) and not any(
        segment in JAVA_RESERVED for segment in name.split("."))


def build_config(args) -> dict:
    if not APP_NAME_RE.match(args.app_name):
        fail(f"--app-name '{args.app_name}' is invalid. Use lowercase letters, digits, "
             "and '-', starting with a letter (progen uses it as a directory name).")
    if not is_java_package(args.base_package):
        fail(f"--base-package '{args.base_package}' is not a valid Java package "
             "(lowercase segments, no Java keywords such as 'class' or 'new').")
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


def patch_java_version(project_dir: Path, version: int) -> bool:
    """Set the Java version in the generated build file. Returns False if nothing matched."""
    pom = project_dir / "pom.xml"
    gradle = project_dir / "build.gradle"
    if pom.exists():
        build_file, pattern, replacement = (
            pom, r"<java\.version>\s*\d+\s*</java\.version>", f"<java.version>{version}</java.version>")
    elif gradle.exists():
        build_file, pattern, replacement = (
            gradle, r"JavaLanguageVersion\.of\(\s*\d+\s*\)", f"JavaLanguageVersion.of({version})")
    else:
        print("WARNING: no pom.xml or build.gradle found; Java version not changed")
        return False
    text = build_file.read_text(encoding="utf-8")
    new, count = re.subn(pattern, replacement, text, count=1)
    if count == 0:
        print(f"WARNING: no Java version setting found in {build_file.name}; "
              f"set Java {version} by hand")
        return False
    build_file.write_text(new, encoding="utf-8")
    sdkmanrc = project_dir / ".sdkmanrc"
    if sdkmanrc.exists():
        print(f"NOTE: update .sdkmanrc to a Java {version} distribution "
              "(CI reads the Java version from it)")
    print(f"Set Java version to {version} in {build_file.name}")
    return True


def jdk_major_version():
    """Major version of the JDK the Maven/Gradle wrapper will use (JAVA_HOME first, as the wrappers do)."""
    java_home = os.environ.get("JAVA_HOME")
    java = str(Path(java_home) / "bin" / "java") if java_home else shutil.which("java")
    if not java or not Path(java).exists():
        return None
    try:
        result = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r'version "(\d+)(?:\.(\d+))?', result.stderr + result.stdout)
    if not match:
        return None
    major = int(match.group(1))
    return int(match.group(2)) if major == 1 and match.group(2) else major


def check_jdk(java_version: int):
    major = jdk_major_version()
    if major is None:
        print("WARNING: java is not on PATH. progen still generates the files, "
              "but its formatting step (spotless) fails.")
        return
    if major > FORMATTER_MAX_JDK:
        fail(f"the JDK in use is {major}. progen's formatter (palantir-java-format) fails on JDKs "
             f"newer than {FORMATTER_MAX_JDK}, and the project then doesn't compile. Point JAVA_HOME "
             f"(and PATH) at a JDK {FORMATTER_MAX_JDK} and run again, or pass --ignore-jdk-check "
             "if a newer formatter has fixed this.", code=6)
    if major < java_version:
        print(f"WARNING: the JDK in use is {major}, but the project targets Java {java_version}. "
              f"The build will fail until JAVA_HOME points at a JDK {java_version}.")


def run_progen(out_dir: Path, config: dict, java_version: int, check_java: bool = True) -> int:
    project_dir = out_dir / config["AppName"]
    if shutil.which("progen") is None:
        fail("progen is not on PATH. Install it: "
             "go install github.com/sivaprasadreddy/progen@latest, "
             "or download a binary from https://github.com/sivaprasadreddy/progen/releases",
             code=3)
    if check_java:
        check_jdk(java_version)

    # Stream progen's output and keep it, to tell a formatting-only failure
    # apart from incomplete generation
    process = subprocess.Popen(["progen", "-c", ".progen.json"], cwd=out_dir,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output = []
    for line in process.stdout:
        print(line, end="")
        output.append(line)
    returncode = process.wait()

    build_file = project_dir / ("pom.xml" if config["BuildTool"] == "Maven" else "build.gradle")
    if not build_file.exists():
        fail(f"progen did not generate {build_file} (exit code {returncode})", code=4)
    if returncode != 0:
        if not any(FORMAT_FAILURE_MARKER in line for line in output):
            fail(f"progen exited with {returncode} and did not report a formatting failure; "
                 f"the project in {project_dir} may be incomplete. Check the output above.", code=4)
        formatter = "./mvnw spotless:apply" if config["BuildTool"] == "Maven" \
            else "./gradlew spotlessApply"
        print(f"WARNING: progen generated the project, but its formatting step failed "
              f"(it needs Java and network access). Run '{formatter}' in {project_dir} later.")
    if java_version != JAVA_VERSION_DEFAULT and not patch_java_version(project_dir, java_version):
        fail(f"Project generated at {project_dir}, but the Java version is still "
             f"{JAVA_VERSION_DEFAULT}.", code=5)
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
    parser.add_argument("--ignore-jdk-check", action="store_true",
                        help=f"Run progen even on a JDK newer than {FORMATTER_MAX_JDK}")
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
        sys.exit(run_progen(out_dir, config, args.java, check_java=not args.ignore_jdk_check))


if __name__ == "__main__":
    main()
