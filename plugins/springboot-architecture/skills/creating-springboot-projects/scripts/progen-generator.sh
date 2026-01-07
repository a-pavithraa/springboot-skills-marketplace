#!/bin/bash

# Progen Command Generator - Generates progen commands based on architecture choice
# Usage: ./progen-generator.sh <architecture> <project-name> <package> [database]

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    echo "Progen Command Generator for Spring Boot Projects"
    echo ""
    echo "Usage: $0 <architecture> <project-name> <package> [database]"
    echo ""
    echo "Arguments:"
    echo "  architecture  Architecture pattern to use"
    echo "  project-name  Name of the project (e.g., product-service)"
    echo "  package       Base package (e.g., com.example.products)"
    echo "  database      Database type (default: postgresql)"
    echo ""
    echo "Architecture options:"
    echo "  layered            Simple CRUD, prototypes (⭐ Low)"
    echo "  package-by-module  3-5 features, medium apps (⭐⭐ Low-Medium)"
    echo "  modular-monolith   Module boundaries + events (⭐⭐ Medium)"
    echo "  tomato             Rich domain + Value Objects (⭐⭐⭐ Medium-High)"
    echo "  ddd-hexagonal      Full DDD + CQRS (⭐⭐⭐⭐ High)"
    echo ""
    echo "Database options:"
    echo "  postgresql (default)"
    echo "  mysql"
    echo "  mariadb"
    echo ""
    echo "Examples:"
    echo "  $0 layered product-api com.example.products"
    echo "  $0 tomato order-service com.example.orders postgresql"
    echo "  $0 modular-monolith inventory-service com.example.inventory mysql"
    echo ""
    echo "What this script does:"
    echo "  1. Generates correct progen command with appropriate features"
    echo "  2. Checks if progen is installed"
    echo "  3. Offers to execute the command"
    echo "  4. Shows post-generation steps for your architecture"
    exit 0
}

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

if [ "$#" -lt 3 ]; then
    echo "Error: Missing required arguments"
    echo "Run '$0 --help' for usage information"
    exit 1
fi

ARCH=$1
PROJECT=$2
PACKAGE=$3
DB=${4:-postgresql}

# Base features
FEATURES="web,data-jpa,validation,flyway,testcontainers,docker,swagger,actuator"

# Architecture-specific features
case $ARCH in
    layered|package-by-module)
        ;;
    modular-monolith|tomato)
        FEATURES="$FEATURES,modulith"
        ;;
    ddd-hexagonal)
        FEATURES="$FEATURES,archunit"
        ;;
    *)
        echo "Error: Invalid architecture '$ARCH'"
        echo "Run '$0 --help' for valid options"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Architecture:${NC} $ARCH"
echo -e "${GREEN}Project:${NC} $PROJECT"
echo -e "${GREEN}Package:${NC} $PACKAGE"
echo -e "${GREEN}Database:${NC} $DB"
echo ""

# Generate command
CMD="progen create --name $PROJECT --package $PACKAGE --build maven --database $DB --features $FEATURES"

echo -e "${YELLOW}Generated progen command:${NC}"
echo "$CMD"
echo ""

# Check if progen is installed
if command -v progen &> /dev/null; then
    echo -e "${GREEN}progen is installed${NC}"
    read -p "Execute now? (y/n): " EXECUTE
    if [ "$EXECUTE" = "y" ]; then
        eval $CMD
        echo ""
        echo -e "${GREEN}✓ Project created!${NC}"
    fi
else
    echo -e "${YELLOW}progen not installed${NC}"
    echo ""
    echo "Install from: https://github.com/sivaprasadreddy/progen/releases"
    echo ""
    echo "Quick install:"
    echo ""
    echo "Linux:"
    echo "  curl -sL https://github.com/sivaprasadreddy/progen/releases/download/v1.0.0/progen-linux-amd64 -o progen"
    echo "  chmod +x progen && sudo mv progen /usr/local/bin/"
    echo ""
    echo "macOS:"
    echo "  curl -sL https://github.com/sivaprasadreddy/progen/releases/download/v1.0.0/progen-darwin-amd64 -o progen"
    echo "  chmod +x progen && sudo mv progen /usr/local/bin/"
    echo ""
    echo "Windows:"
    echo "  Download: https://github.com/sivaprasadreddy/progen/releases/download/v1.0.0/progen-windows-amd64.exe"
    echo "  Rename to progen.exe and add to PATH"
fi

# Show post-generation steps
if [ "$ARCH" = "tomato" ] || [ "$ARCH" = "ddd-hexagonal" ]; then
    echo ""
    echo -e "${YELLOW}Manual step required - add to pom.xml:${NC}"
    echo "<dependency>"
    echo "    <groupId>io.hypersistence</groupId>"
    echo "    <artifactId>hypersistence-utils-hibernate-71</artifactId>"
    echo "    <version>3.14.1</version>"
    echo "</dependency>"
fi
