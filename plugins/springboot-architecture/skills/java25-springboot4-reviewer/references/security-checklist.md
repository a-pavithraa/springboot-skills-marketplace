# Security Review Checklist

## Table of Contents

1. [OWASP Top 10 (2021)](#owasp-top-10)
2. [Spring Security Patterns](#spring-security-patterns)
3. [Authentication](#authentication)
4. [Authorization](#authorization)
5. [Input Validation](#input-validation)
6. [Cryptography](#cryptography)
7. [Session Management](#session-management)
8. [API Security](#api-security)
9. [Logging and Monitoring](#logging-and-monitoring)

---

## OWASP Top 10

### A01:2021 – Broken Access Control

❌ **Insecure: No authorization checks**
```java
@GetMapping("/admin/users")
public List<User> getAllUsers() {
    return userRepository.findAll();  // Anyone can access!
}
```

✅ **Secure: Proper authorization**
```java
@GetMapping("/admin/users")
@PreAuthorize("hasRole('ADMIN')")
public List<User> getAllUsers() {
    return userRepository.findAll();
}
```

✅ **Secure: Method-level security**
```java
@Service
public class UserService {
    @PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")
    public User getUser(Long userId) {
        return userRepository.findById(userId)
            .orElseThrow(() -> new UserNotFoundException(userId));
    }
}
```

**Review Points:**
- [ ] All sensitive endpoints have authorization checks
- [ ] Authorization is method-level, not just URL-based
- [ ] Users can only access their own resources (or have proper role)

---

### A02:2021 – Cryptographic Failures

❌ **Insecure: Plain text passwords**
```java
@Entity
public class User {
    private String password;  // Stored as plain text!
}

user.setPassword(request.getPassword());  // NO!
```

✅ **Secure: Encrypted passwords**
```java
@Service
public class UserService {
    private final PasswordEncoder passwordEncoder;

    public void createUser(UserRequest request) {
        User user = new User();
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        userRepository.save(user);
    }
}

@Configuration
public class SecurityConfig {
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();  // Or Argon2PasswordEncoder
    }
}
```

❌ **Insecure: Weak encryption**
```java
// MD5/SHA1 are broken
String hash = DigestUtils.md5Hex(password);
```

✅ **Secure: Strong algorithms**
```java
// BCrypt or Argon2
String hash = passwordEncoder.encode(password);
```

❌ **Insecure: Sensitive data in logs**
```java
log.info("User login: {}", userRequest);  // May contain password!
```

✅ **Secure: Sanitize logs**
```java
log.info("User login attempt: username={}", userRequest.getUsername());
```

**Review Points:**
- [ ] Passwords use BCrypt or Argon2 (never MD5/SHA1)
- [ ] Sensitive data (passwords, tokens, PII) never logged
- [ ] Secrets not hardcoded (use environment variables)
- [ ] TLS/HTTPS enforced for all endpoints

---

### A03:2021 – Injection

#### SQL Injection

❌ **Insecure: String concatenation**
```java
@Query(value = "SELECT * FROM users WHERE username = '" + username + "'", nativeQuery = true)
List<User> findByUsername(String username);
```

✅ **Secure: Parameterized queries**
```java
@Query("SELECT u FROM User u WHERE u.username = :username")
List<User> findByUsername(@Param("username") String username);
```

✅ **Secure: JPA methods**
```java
List<User> findByUsername(String username);  // Spring Data JPA
```

#### NoSQL Injection

❌ **Insecure: Direct query building**
```java
Query query = new Query(Criteria.where("username").is(username));
// If username = {$ne: null}, returns all users!
```

✅ **Secure: Validate input**
```java
if (!username.matches("^[a-zA-Z0-9_]+$")) {
    throw new IllegalArgumentException("Invalid username");
}
Query query = new Query(Criteria.where("username").is(username));
```

#### Command Injection

❌ **Insecure: Runtime.exec with user input**
```java
Runtime.getRuntime().exec("convert " + userFile + " output.pdf");
```

✅ **Secure: Use libraries, not shell commands**
```java
// Use Apache PDFBox, iText, etc. instead of shell commands
```

**Review Points:**
- [ ] All queries use parameterized queries or JPA methods
- [ ] No `Runtime.exec()` or `ProcessBuilder` with user input
- [ ] Input validated before use in queries

---

### A04:2021 – Insecure Design

❌ **Insecure: No rate limiting**
```java
@PostMapping("/login")
public ResponseEntity<TokenResponse> login(@RequestBody LoginRequest request) {
    // No rate limiting - brute force attacks possible
}
```

✅ **Secure: Rate limiting**
```java
@PostMapping("/login")
@RateLimiter(name = "login", fallbackMethod = "loginRateLimitFallback")
public ResponseEntity<TokenResponse> login(@RequestBody LoginRequest request) {
    // Rate limited
}

private ResponseEntity<TokenResponse> loginRateLimitFallback(LoginRequest request, Throwable t) {
    return ResponseEntity.status(429).build();  // Too Many Requests
}
```

✅ **Secure: Account lockout**
```java
@Service
public class LoginService {
    private static final int MAX_ATTEMPTS = 5;
    private final Map<String, Integer> loginAttempts = new ConcurrentHashMap<>();

    public void recordLoginFailure(String username) {
        int attempts = loginAttempts.getOrDefault(username, 0) + 1;
        loginAttempts.put(username, attempts);

        if (attempts >= MAX_ATTEMPTS) {
            // Lock account or add delay
            throw new AccountLockedException("Too many failed attempts");
        }
    }

    public void recordLoginSuccess(String username) {
        loginAttempts.remove(username);
    }
}
```

**Review Points:**
- [ ] Rate limiting on authentication endpoints
- [ ] Account lockout after N failed attempts
- [ ] CAPTCHA for sensitive operations
- [ ] Proper error messages (don't leak info: "Invalid credentials" not "User not found")

---

### A05:2021 – Security Misconfiguration

❌ **Insecure: Defaults exposed**
```yaml
# application.properties
spring.h2.console.enabled=true  # In production!
management.endpoints.web.exposure.include=*  # All endpoints exposed!
```

✅ **Secure: Minimal exposure**
```yaml
# application-prod.properties
spring.h2.console.enabled=false
management.endpoints.web.exposure.include=health,metrics
management.endpoint.health.show-details=when-authorized
```

❌ **Insecure: Verbose error messages**
```java
@ExceptionHandler(Exception.class)
public ResponseEntity<String> handleException(Exception ex) {
    return ResponseEntity.status(500).body(ex.getMessage());  // Leaks stack trace!
}
```

✅ **Secure: Generic error messages**
```java
@ExceptionHandler(Exception.class)
public ProblemDetail handleException(Exception ex) {
    log.error("Internal error", ex);  // Log details server-side
    return ProblemDetail.forStatusAndDetail(
        HttpStatus.INTERNAL_SERVER_ERROR,
        "An unexpected error occurred"  // Generic message to client
    );
}
```

**Review Points:**
- [ ] Debug endpoints disabled in production
- [ ] Error messages don't leak sensitive info
- [ ] CORS properly configured (not `allowedOrigins=*`)
- [ ] Security headers enabled (CSP, HSTS, X-Frame-Options)

---

### A06:2021 – Vulnerable and Outdated Components

**Review Points:**
- [ ] All dependencies up to date (check with `mvn versions:display-dependency-updates`)
- [ ] No known vulnerabilities (check with `mvn dependency-check:check`)
- [ ] Spring Boot BOM manages versions
- [ ] No deprecated APIs in use

---

### A07:2021 – Identification and Authentication Failures

❌ **Insecure: Weak password policy**
```java
// No password requirements
```

✅ **Secure: Strong password policy**
```java
@Service
public class PasswordValidator {
    private static final Pattern PASSWORD_PATTERN = Pattern.compile(
        "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{12,}$"
    );

    public void validate(String password) {
        if (!PASSWORD_PATTERN.matcher(password).matches()) {
            throw new WeakPasswordException(
                "Password must be at least 12 characters with uppercase, lowercase, digit, and special character"
            );
        }
    }
}
```

❌ **Insecure: Predictable session IDs**
```java
String sessionId = username + System.currentTimeMillis();  // Predictable!
```

✅ **Secure: Random session IDs**
```java
// Spring Security handles this automatically
// Or use SecureRandom for custom tokens
SecureRandom random = new SecureRandom();
byte[] bytes = new byte[32];
random.nextBytes(bytes);
String token = Base64.getUrlEncoder().encodeToString(bytes);
```

**Review Points:**
- [ ] Strong password policy enforced
- [ ] Multi-factor authentication for sensitive operations
- [ ] Session IDs cryptographically random
- [ ] Secure session timeout (15-30 minutes)

---

### A08:2021 – Software and Data Integrity Failures

❌ **Insecure: Deserialization without validation**
```java
ObjectInputStream ois = new ObjectInputStream(request.getInputStream());
Object obj = ois.readObject();  // Arbitrary code execution risk!
```

✅ **Secure: Use JSON with validation**
```java
@PostMapping("/data")
public ResponseEntity<Result> processData(@Valid @RequestBody DataRequest request) {
    // Jackson handles deserialization safely with validation
}
```

**Review Points:**
- [ ] No Java serialization (use JSON instead)
- [ ] Dependencies verified (checksums, signatures)
- [ ] CI/CD pipeline secured

---

### A09:2021 – Security Logging and Monitoring Failures

❌ **Insecure: No security logging**
```java
@PostMapping("/login")
public ResponseEntity<TokenResponse> login(@RequestBody LoginRequest request) {
    // No logging of authentication attempts
}
```

✅ **Secure: Comprehensive security logging**
```java
@PostMapping("/login")
public ResponseEntity<TokenResponse> login(@RequestBody LoginRequest request) {
    log.info("Login attempt: username={}, ip={}",
        request.getUsername(),
        httpRequest.getRemoteAddr()
    );

    try {
        TokenResponse response = authService.authenticate(request);
        log.info("Login successful: username={}", request.getUsername());
        return ResponseEntity.ok(response);
    } catch (AuthenticationException e) {
        log.warn("Login failed: username={}, reason={}",
            request.getUsername(),
            e.getMessage()
        );
        throw e;
    }
}
```

**Review Points:**
- [ ] All authentication attempts logged (success and failure)
- [ ] Authorization failures logged
- [ ] Sensitive operations logged (password reset, role changes)
- [ ] Logs include timestamp, user, IP, action
- [ ] Logs don't contain sensitive data (passwords, tokens)

---

### A10:2021 – Server-Side Request Forgery (SSRF)

❌ **Insecure: Unvalidated URL**
```java
@GetMapping("/fetch")
public String fetchContent(@RequestParam String url) {
    return restClient.get().uri(url).retrieve().body(String.class);
    // Can access internal services: http://localhost:8080/admin
}
```

✅ **Secure: URL validation**
```java
@GetMapping("/fetch")
public String fetchContent(@RequestParam String url) {
    if (!isAllowedUrl(url)) {
        throw new IllegalArgumentException("URL not allowed");
    }
    return restClient.get().uri(url).retrieve().body(String.class);
}

private boolean isAllowedUrl(String url) {
    try {
        URI uri = new URI(url);
        String host = uri.getHost();

        // Whitelist approach
        return ALLOWED_HOSTS.contains(host);

        // Or blacklist localhost, private IPs
        if (host.equals("localhost") ||
            host.equals("127.0.0.1") ||
            host.startsWith("192.168.") ||
            host.startsWith("10.") ||
            host.startsWith("172.16.")) {
            return false;
        }
        return true;
    } catch (URISyntaxException e) {
        return false;
    }
}
```

**Review Points:**
- [ ] All user-provided URLs validated
- [ ] Whitelist approach preferred
- [ ] Internal IPs/hostnames blocked

---

## Spring Security Patterns

### Security Configuration

✅ **Modern Spring Security (Spring Boot 4)**
```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
            )
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .sessionManagement(session -> session
                .sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtConverter()))
            );

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();  // Or Argon2PasswordEncoder
    }
}
```

### JWT Security

❌ **Insecure: Weak JWT secret**
```java
String secret = "secret";  // Too short, too weak
```

✅ **Secure: Strong JWT secret**
```java
@Value("${jwt.secret}")
private String secret;  // From environment, at least 256 bits

// Or better: use asymmetric keys (RS256)
```

✅ **Secure: JWT validation**
```java
public boolean validateToken(String token) {
    try {
        Jwts.parserBuilder()
            .setSigningKey(key)
            .build()
            .parseClaimsJws(token);
        return true;
    } catch (JwtException | IllegalArgumentException e) {
        log.error("Invalid JWT token: {}", e.getMessage());
        return false;
    }
}
```

**Review Points:**
- [ ] JWT secret at least 256 bits (or use RS256)
- [ ] JWT expiration set (short-lived: 15-60 minutes)
- [ ] Refresh tokens implemented for long-lived sessions
- [ ] Token validation on every request

---

## Input Validation

✅ **Bean Validation**
```java
public record CreateUserRequest(
    @NotBlank(message = "Username is required")
    @Size(min = 3, max = 50)
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "Username can only contain alphanumeric characters and underscores")
    String username,

    @NotBlank(message = "Email is required")
    @Email(message = "Email must be valid")
    String email,

    @NotBlank(message = "Password is required")
    @Size(min = 12, message = "Password must be at least 12 characters")
    String password
) {}

@PostMapping("/users")
public ResponseEntity<User> createUser(@Valid @RequestBody CreateUserRequest request) {
    // Validation happens automatically
    return ResponseEntity.ok(userService.create(request));
}
```

✅ **Custom validators**
```java
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = StrongPasswordValidator.class)
public @interface StrongPassword {
    String message() default "Password must meet strength requirements";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

public class StrongPasswordValidator implements ConstraintValidator<StrongPassword, String> {
    @Override
    public boolean isValid(String password, ConstraintValidatorContext context) {
        if (password == null) return false;

        return password.length() >= 12 &&
               password.matches(".*[a-z].*") &&
               password.matches(".*[A-Z].*") &&
               password.matches(".*\\d.*") &&
               password.matches(".*[@$!%*?&].*");
    }
}
```

**Review Points:**
- [ ] All user input validated with `@Valid`
- [ ] Size limits on all string inputs
- [ ] Pattern validation where applicable
- [ ] Custom validators for complex rules

---

## Review Checklist

### Critical Security Issues

- [ ] **SQL Injection**: All queries parameterized or use JPA methods
- [ ] **XSS**: Output encoding enabled, no `innerHTML` with user input
- [ ] **Authentication**: Passwords hashed with BCrypt/Argon2
- [ ] **Authorization**: All sensitive endpoints have `@PreAuthorize`
- [ ] **CSRF**: CSRF protection enabled for state-changing operations
- [ ] **Secrets**: No hardcoded secrets, use environment variables
- [ ] **Logging**: No sensitive data in logs (passwords, tokens, PII)

### Best Practices

- [ ] TLS/HTTPS enforced
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options)
- [ ] Rate limiting on authentication endpoints
- [ ] Input validation on all user input
- [ ] Error messages don't leak info
- [ ] Session timeout configured (15-30 minutes)
- [ ] Dependencies up to date, no known vulnerabilities

---

## Official Documentation

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [Spring Security Reference](https://docs.spring.io/spring-security/reference/)
- [Spring Security Architecture](https://spring.io/guides/topicals/spring-security-architecture)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Spring Boot Security Best Practices](https://docs.spring.io/spring-boot/reference/web/spring-security.html)
- [JWT Best Practices (RFC 8725)](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
