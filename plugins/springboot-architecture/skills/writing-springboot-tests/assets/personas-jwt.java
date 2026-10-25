package {{PACKAGE}};

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.boot.test.context.TestComponent;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/**
 * Signs a MockMvc request in as a named caller of a resource server that accepts JWT bearer tokens. The claims are
 * what the identity provider puts in the token, and the roles come from the app's own JwtAuthenticationConverter
 * (exposed as a bean, or built here the way the app builds it), so every test that uses a persona also checks the
 * conversion. jwt() alone uses its own
 * converter, which reads only "scope": a "roles" claim set on it never becomes ROLE_ADMIN, and a role set with
 * .authorities(...) passes even when the app's converter is broken. Use with @Import(Personas.class):
 *
 *   mvc.post().uri("/api/orders").with(personas.as("customer"))
 *
 * Verified on Spring Boot 4.1.1 / Spring Security 7.
 */
@TestComponent
class Personas {

    /** The team's callers and the token claims their provider sends, with the provider's claim names. */
    static final Map<String, Map<String, Object>> CLAIMS = Map.of(
            "customer", Map.of("sub", "customer-1", "roles", List.of()),
            "admin", Map.of("sub", "admin-1", "roles", List.of("ADMIN")),
            "auditor", Map.of("sub", "auditor-1", "roles", List.of("AUDITOR")));

    static final List<String> NAMES = List.copyOf(CLAIMS.keySet());

    private final JwtAuthenticationConverter converter;

    Personas(JwtAuthenticationConverter converter) {
        this.converter = converter;
    }

    RequestPostProcessor as(String persona) {
        Map<String, Object> claims = CLAIMS.get(persona);
        if (claims == null) {
            throw new IllegalArgumentException("No persona " + persona + ". Add it to Personas.CLAIMS");
        }
        return jwt().jwt(token -> token.claims(all -> all.putAll(claims)))
                .authorities(token -> new ArrayList<GrantedAuthority>(converter.convert(token).getAuthorities()));
    }
}
