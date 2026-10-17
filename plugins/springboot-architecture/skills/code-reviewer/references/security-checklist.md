# Security Review Checklist

Organized by [OWASP Top 10:2025](https://owasp.org/Top10/). Targets Spring Boot 4 / Spring Security 7. Report exploitability and the affected entry point, not only the rule.

## Contents

1. [OWASP Top 10:2025](#owasp-top-102025)
2. [Spring Security 7 configuration](#spring-security-7-configuration)
3. [Tokens and JWT](#tokens-and-jwt)
4. [Review checklist](#review-checklist)

---

## OWASP Top 10:2025

### A01 Broken Access Control (includes SSRF)

| Flag | Fix |
|------|-----|
| Privileged endpoint with no rule in the filter chain and no `@PreAuthorize` | Deny by default (`anyRequest().authenticated()`), add role/authority checks |
| Object fetched by ID with no ownership check (IDOR): `repository.findById(id)` for the current user's data | Check ownership: `@PreAuthorize("#userId == authentication.principal.id")`, or query by `(id, ownerId)` |
| URL rules only; services callable from other entry points (messaging, schedulers) | Method security (`@EnableMethodSecurity`) on services |
| Client-controlled role or tenant fields bound into entities | Bind request DTOs, not entities; set owner/tenant on the server |

**SSRF.** Flag any outbound call to a URL or host that comes from the request.

- Use an allowlist of hosts, and fail closed when the host is missing or not on it.
- Disable redirects for those calls, or re-check the target after a redirect. An allowed host can redirect to an internal one.
- If an allowlist is not possible, resolve the host and reject loopback, site-local, link-local, and any-local addresses (`InetAddress.isLoopbackAddress()`, `isSiteLocalAddress()`, `isLinkLocalAddress()`, `isAnyLocalAddress()`), plus `169.254.169.254`. Check every resolved address, and connect to the checked address so DNS rebinding cannot swap it. String prefix checks like `host.startsWith("172.16.")` miss `172.17`-`172.31`, IPv6, and encoded forms.

### A02 Security Misconfiguration

| Flag | Fix |
|------|-----|
| `management.endpoints.web.exposure.include=*` in production | Expose `health` (and metrics behind auth) only |
| `management.endpoint.health.show-details=always` | `when-authorized` |
| `spring.h2.console.enabled=true` outside local profiles | Disable |
| CORS `allowedOrigins("*")` with credentials, or `@CrossOrigin` everywhere | Explicit origins in one `CorsConfigurationSource` |
| Security headers disabled (`headers(h -> h.disable())`) | Keep Spring Security defaults; add CSP for browser apps; HSTS behind TLS |
| Stack traces or exception messages in responses (`ex.getMessage()` in a 500) | `ProblemDetail` with a generic message; log details on the server; `server.error.include-stacktrace=never` (default) |

### A03 Software Supply Chain Failures

- [ ] Versions come from the Boot BOM; no unmanaged overrides of Spring, Jackson, or Netty without a reason.
- [ ] A dependency scanner runs in CI (OWASP Dependency-Check, GitHub Dependabot/Renovate, or similar).
- [ ] No unmaintained libraries or end-of-life runtimes.
- [ ] Build plugins and Maven/Gradle wrappers come from trusted repositories, with wrapper checksums verified.

### A04 Cryptographic Failures

| Flag | Fix |
|------|-----|
| Plain-text, MD5, SHA-1, or unsalted SHA-256 passwords | `PasswordEncoderFactories.createDelegatingPasswordEncoder()` (bcrypt by default, `{id}` prefix allows later upgrades), or Argon2 |
| `new Random()` for tokens, reset codes, IDs that must be secret | `SecureRandom`, 32+ bytes, Base64URL |
| Secrets in source or `application.properties` | Environment variables or a secret manager |
| HTTP between services that carry credentials or personal data | TLS |
| Passwords, tokens, or full request bodies in logs | Log identifiers only |

For key derivation (not passwords), see `java-25-features.md` (`javax.crypto.KDF`, HKDF).

### A05 Injection

| Flag | Fix |
|------|-----|
| String concatenation into JPQL/SQL (`"... where name = '" + name + "'"`), including `nativeQuery = true` and `JdbcClient.sql(...)` | Bind parameters (`:name`, `?`) |
| User input as a sort property or column name | Map to an allowlist of properties before `Sort.by(...)` |
| MongoDB: a request `Map`/`Document` used as query criteria, or a JSON query built by string concatenation (`new BasicQuery("{name: '" + n + "'}")`) | Typed parameters: `Criteria.where("name").is(name)` with a `String` is safe; `@Query("{ 'name': ?0 }")` binds safely |
| `Runtime.exec` / `ProcessBuilder` with user input | Avoid; if needed, fixed command plus argument list, never a shell string |
| SpEL or template expressions built from user input | Never evaluate user input |
| Unescaped output in Thymeleaf (`th:utext`) | `th:text` |

### A06 Insecure Design

- [ ] Login, password reset, and OTP endpoints have rate limits (gateway, Bucket4j, or Resilience4j `@RateLimiter`). In-memory counters do not work across instances.
- [ ] Failed-login handling slows attackers without letting them lock out any account at will (progressive delays, CAPTCHA, or MFA rather than hard lockout).
- [ ] Error messages do not reveal whether a user exists ("Invalid credentials").
- [ ] Business limits are enforced on the server (quantities, amounts, workflow order).

### A07 Authentication Failures

- [ ] Passwords: minimum length (NIST SP 800-63B rev. 4: 15 characters without MFA, 8 with MFA), maximum at least 64, all characters allowed, checked against breached-password lists. No forced character-class rules and no periodic forced changes. Flag regexes that require "uppercase + digit + special".
- [ ] MFA for admin and sensitive operations.
- [ ] Session fixation protection stays on (Spring Security default); session cookies `Secure`, `HttpOnly`, `SameSite`.
- [ ] Idle session timeout set (`server.servlet.session.timeout`).

### A08 Software or Data Integrity Failures

- [ ] No `ObjectInputStream.readObject()` on untrusted data.
- [ ] No Jackson default typing on untrusted input (`activateDefaultTyping`, `enableUnsafeDefaultTyping`). If polymorphic types are needed, use a `PolymorphicTypeValidator` limited to app packages.
- [ ] Webhooks and callbacks verify signatures.
- [ ] CI artifacts are signed or checksummed.

### A09 Security Logging and Alerting Failures

- [ ] Login success/failure, access denied, password and role changes are logged with time, user, source IP, and action. Spring Security publishes `AuthenticationSuccessEvent` / `AbstractAuthenticationFailureEvent` / `AuthorizationDeniedEvent`; listen to them instead of logging in controllers.
- [ ] Logs never contain passwords, tokens, or full personal data.
- [ ] User input in logs cannot forge log lines (structured logging, or strip CR/LF).
- [ ] Alerts exist for spikes in authentication failures.

### A10 Mishandling of Exceptional Conditions

| Flag | Fix |
|------|-----|
| `catch (Exception e) { return true; }` around an authorization or validation check | Fail closed: deny on error |
| Swallowed exceptions in security filters or token validation | Log and reject |
| Exception details returned to clients | Generic `ProblemDetail`; details only in server logs |
| Missing timeouts on outbound calls | Connect and read timeouts (`spring.http.clients.*`), so failures do not hang threads |
| Partial updates left after an exception | Transaction boundaries around multi-step writes |

---

## Spring Security 7 configuration

```java
@Configuration
@EnableMethodSecurity
class SecurityConfig {

    // Stateless JSON API with bearer tokens
    @Bean
    SecurityFilterChain api(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/api/**")
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .csrf(csrf -> csrf.disable())   // no cookies carry credentials here
            .oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()));
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }
}
```

Review rules:

- **CSRF:** keep it on for browser apps that use session cookies. Disabling it is correct only when no cookie carries credentials (bearer-token APIs). Flag `csrf.disable()` together with form login or session cookies.
- **Spring Security 7 removals:** `AntPathRequestMatcher` and `MvcRequestMatcher` are gone (use `requestMatchers("/path/**")` or `PathPatternRequestMatcher`), and the `.and()` chaining DSL is gone (use lambda customizers). Old code does not compile.
- `@EnableWebSecurity` is optional in Boot. `@EnableMethodSecurity` already enables `@PreAuthorize`/`@PostAuthorize` (`prePostEnabled` defaults to `true`).
- Order several `SecurityFilterChain` beans with `securityMatcher(...)`; a chain without a matcher catches everything.
- Test rules with `spring-boot-starter-security-test` (`@WithMockUser`, `SecurityMockMvcRequestPostProcessors.jwt()`).

---

## Tokens and JWT

- Prefer Spring Security's resource server (`spring-boot-starter-oauth2-resource-server`, `spring.security.oauth2.resourceserver.jwt.issuer-uri` or `jwk-set-uri`) over hand-written JWT parsing. It validates signature, expiry, and issuer.
- If the code parses JWTs itself (JJWT 0.12+): `Jwts.parser().verifyWith(key).build().parseSignedClaims(token)`. Flag the pre-0.12 `parserBuilder()/setSigningKey()/parseClaimsJws()` API.
- HS256 keys need at least 256 bits from a secret store. Prefer asymmetric keys (RS256/ES256) when other services verify tokens.
- Check `exp`, `iss`, and `aud`. Reject `alg: none`. Access tokens are short-lived (minutes); refresh tokens are revocable.
- Do not put tokens in URLs or `localStorage` for browser apps when an `HttpOnly` cookie (with CSRF protection) is possible.

---

## Review checklist

Critical:

- [ ] Every privileged endpoint and service method has an authorization rule; object-level ownership is checked
- [ ] No string-built SQL/JPQL/Mongo queries; no user input in sort fields without an allowlist
- [ ] Passwords via `DelegatingPasswordEncoder`/bcrypt/Argon2; no secrets in source or logs
- [ ] CSRF on for cookie-based sessions; disabled only for bearer-token APIs
- [ ] No SSRF: user-supplied URLs allowlisted, redirects controlled
- [ ] No unsafe deserialization or Jackson default typing on untrusted input
- [ ] Errors fail closed and do not leak details

Important:

- [ ] Actuator exposure minimal; H2 console off; CORS explicit
- [ ] Rate limits on authentication endpoints; no account-enumeration messages
- [ ] Password policy follows NIST length rules, not composition rules
- [ ] Security events logged; dependency scanning in CI
- [ ] Spring Security 7 APIs (no `AntPathRequestMatcher`, no `.and()`)

## Official documentation

- [OWASP Top 10:2025](https://owasp.org/Top10/), [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Spring Security Reference](https://docs.spring.io/spring-security/reference/)
- [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [JWT Best Current Practices (RFC 8725)](https://datatracker.ietf.org/doc/html/rfc8725)
