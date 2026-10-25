package {{PACKAGE}};

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.oidcLogin;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.boot.test.context.TestComponent;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.mapping.GrantedAuthoritiesMapper;
import org.springframework.security.oauth2.core.oidc.OidcIdToken;
import org.springframework.security.oauth2.core.oidc.user.OidcUserAuthority;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/**
 * Signs a MockMvc request in as a named user of an app that logs in with oauth2Login and keeps the login in a
 * server-side session. The claims are what the identity provider puts in the ID token, and the roles come from the
 * app's own GrantedAuthoritiesMapper (the one passed to userInfoEndpoint().userAuthoritiesMapper(), exposed as a
 * bean, or constructed here when the app creates it inline, such as new RoleClaimsMapper()), so every
 * test that uses a persona also checks the mapping. oidcLogin() alone skips the mapper: a "roles"
 * claim set on it never becomes ROLE_ADMIN, and a role set with .authorities(...) passes even when the mapper is
 * broken. Use with @Import(Personas.class):
 *
 *   mvc.post().uri("/api/orders").with(personas.as("customer")).with(csrf())
 *
 * Verified on Spring Boot 4.1.1 / Spring Security 7.
 */
@TestComponent
class Personas {

    /** The team's users and the ID-token claims their provider sends, with the provider's claim names. */
    static final Map<String, Map<String, Object>> CLAIMS = Map.of(
            "customer", Map.of("sub", "customer-1", "roles", List.of()),
            "admin", Map.of("sub", "admin-1", "roles", List.of("ADMIN")),
            "auditor", Map.of("sub", "auditor-1", "roles", List.of("AUDITOR")));

    static final List<String> NAMES = List.copyOf(CLAIMS.keySet());

    private final GrantedAuthoritiesMapper rolesMapper;

    Personas(GrantedAuthoritiesMapper rolesMapper) {
        this.rolesMapper = rolesMapper;
    }

    RequestPostProcessor as(String persona) {
        Map<String, Object> claims = claims(persona);
        OidcIdToken idToken = new OidcIdToken("token", Instant.now(), Instant.now().plusSeconds(300), claims);
        return oidcLogin()
                .idToken(token -> token.claims(all -> all.putAll(claims)))
                .authorities(new ArrayList<GrantedAuthority>(
                        rolesMapper.mapAuthorities(List.of(new OidcUserAuthority(idToken)))));
    }

    private static Map<String, Object> claims(String persona) {
        Map<String, Object> claims = CLAIMS.get(persona);
        if (claims == null) {
            throw new IllegalArgumentException("No persona " + persona + ". Add it to Personas.CLAIMS");
        }
        return claims;
    }
}
