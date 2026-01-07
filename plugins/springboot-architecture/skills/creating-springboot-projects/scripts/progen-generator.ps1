# Progen Command Generator for Spring Boot Projects (Windows PowerShell)
# Usage: .\progen-generator.ps1 -Architecture <arch> -ProjectName <name> -Package <pkg> [-Database <db>]

param(
    [Parameter(Mandatory=$false)]
    [switch]$Help,

    [Parameter(Mandatory=$false)]
    [ValidateSet("layered", "package-by-module", "modular-monolith", "tomato", "ddd-hexagonal")]
    [string]$Architecture,

    [Parameter(Mandatory=$false)]
    [string]$ProjectName,

    [Parameter(Mandatory=$false)]
    [string]$Package,

    [Parameter(Mandatory=$false)]
    [ValidateSet("postgresql", "mysql", "mariadb")]
    [string]$Database = "postgresql"
)

function Show-Help {
    Write-Host "Progen Command Generator for Spring Boot Projects" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\progen-generator.ps1 -Architecture <arch> -ProjectName <name> -Package <pkg> [-Database <db>]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Architecture  Architecture pattern to use (required)"
    Write-Host "  -ProjectName   Name of the project (required)"
    Write-Host "  -Package       Base package (required)"
    Write-Host "  -Database      Database type (optional, default: postgresql)"
    Write-Host ""
    Write-Host "Architecture options:"
    Write-Host "  layered            Simple CRUD, prototypes (⭐ Low)"
    Write-Host "  package-by-module  3-5 features, medium apps (⭐⭐ Low-Medium)"
    Write-Host "  modular-monolith   Module boundaries + events (⭐⭐ Medium)"
    Write-Host "  tomato             Rich domain + Value Objects (⭐⭐⭐ Medium-High)"
    Write-Host "  ddd-hexagonal      Full DDD + CQRS (⭐⭐⭐⭐ High)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\progen-generator.ps1 -Architecture layered -ProjectName product-api -Package com.example.products"
    Write-Host "  .\progen-generator.ps1 -Architecture tomato -ProjectName order-service -Package com.example.orders"
    Write-Host ""
    exit 0
}

if ($Help) {
    Show-Help
}

if (-not $Architecture -or -not $ProjectName -or -not $Package) {
    Write-Host "Error: Missing required parameters" -ForegroundColor Red
    Write-Host "Run '.\progen-generator.ps1 -Help' for usage information"
    exit 1
}

# Base features
$Features = "web,data-jpa,validation,flyway,testcontainers,docker,swagger,actuator"

# Architecture-specific features
switch ($Architecture) {
    "layered" { }
    "package-by-module" { }
    "modular-monolith" { $Features = "$Features,modulith" }
    "tomato" { $Features = "$Features,modulith" }
    "ddd-hexagonal" { $Features = "$Features,archunit" }
}

Write-Host ""
Write-Host "Architecture: " -NoNewline; Write-Host $Architecture -ForegroundColor Green
Write-Host "Project: " -NoNewline; Write-Host $ProjectName -ForegroundColor Green
Write-Host "Package: " -NoNewline; Write-Host $Package -ForegroundColor Green
Write-Host "Database: " -NoNewline; Write-Host $Database -ForegroundColor Green
Write-Host ""

# Generate command
$Cmd = "progen create --name $ProjectName --package $Package --build maven --database $Database --features $Features"

Write-Host "Generated progen command:" -ForegroundColor Yellow
Write-Host $Cmd
Write-Host ""

# Check if progen is installed
$ProgenExists = Get-Command progen -ErrorAction SilentlyContinue

if ($ProgenExists) {
    Write-Host "progen is installed" -ForegroundColor Green
    $Execute = Read-Host "Execute now? (y/n)"
    if ($Execute -eq "y") {
        Invoke-Expression $Cmd
        Write-Host ""
        Write-Host "✓ Project created!" -ForegroundColor Green
    }
} else {
    Write-Host "progen not installed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Download from: https://github.com/sivaprasadreddy/progen/releases/download/v1.0.0/progen-windows-amd64.exe"
    Write-Host "Rename to progen.exe and add to PATH"
    Write-Host ""
    Write-Host "Or visit: https://github.com/sivaprasadreddy/progen/releases"
}

# Show post-generation steps
if ($Architecture -eq "tomato" -or $Architecture -eq "ddd-hexagonal") {
    Write-Host ""
    Write-Host "Manual step required - add to pom.xml:" -ForegroundColor Yellow
    Write-Host @"
<dependency>
    <groupId>io.hypersistence</groupId>
    <artifactId>hypersistence-utils-hibernate-71</artifactId>
    <version>3.14.1</version>
</dependency>
"@
}
