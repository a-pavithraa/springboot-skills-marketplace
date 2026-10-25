package {{PACKAGE}};

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;

import java.util.List;
import java.util.Map;
import org.springframework.boot.test.context.TestComponent;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/**
 * Signs a MockMvc request in as a named user of an app whose users and roles are in its own database, loaded by a
 * UserDetailsService (form login or HTTP Basic). The user is loaded by the app's own UserDetailsService, so every
 * test that uses a persona also checks how stored roles become authorities. user("ann").roles("ADMIN") skips it and
 * passes even when the service loses the roles. The users must exist: seed them before each test, for example with
 * @Sql("/sql/personas.sql") on the test class. Use with @Import(Personas.class):
 *
 *   mvc.post().uri("/api/orders").with(personas.as("customer")).with(csrf())
 *
 * Verified on Spring Boot 4.1.1 / Spring Security 7.
 */
@TestComponent
class Personas {

    /** Persona name and the username of the seeded user. */
    static final Map<String, String> USERS = Map.of(
            "customer", "customer@example.com",
            "admin", "admin@example.com",
            "auditor", "auditor@example.com");

    static final List<String> NAMES = List.copyOf(USERS.keySet());

    private final UserDetailsService users;

    Personas(UserDetailsService users) {
        this.users = users;
    }

    RequestPostProcessor as(String persona) {
        String username = USERS.get(persona);
        if (username == null) {
            throw new IllegalArgumentException("No persona " + persona + ". Add it to Personas.USERS");
        }
        return user(users.loadUserByUsername(username));
    }
}
