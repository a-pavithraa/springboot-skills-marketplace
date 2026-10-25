package {{PACKAGE}};

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;

import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpMethod;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

/**
 * Who may call each route. A route missing from ROUTES fails the build, so no endpoint ships without a decision,
 * and each route is called as every persona (personas-*.java), not only the ones a feature test happened to use.
 * This checks roles, not records: whether one user can read another user's data needs a feature test with two
 * users. With a database, add @Transactional so calls that write roll back, and seed the personas the way
 * Personas says.
 *
 * Verified on Spring Boot 4.1.1 against planted gaps: a route nobody listed, an admin rule narrowed so a sibling
 * route lost it, a role mapping that loses the roles, and a dropped @PreAuthorize.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(Personas.class)
class RouteAccessTests {

    /** Allowed: every signed-in persona. */
    static final Set<String> SIGNED_IN = Set.of("*");

    /** Allowed: anyone, signed in or not. */
    static final Set<String> PUBLIC = Set.of("anonymous", "*");

    /** A route as Spring maps it, a request that reaches it, and who may call it. */
    record Route(String route, String uri, Set<String> allowed) {}

    static final List<Route> ROUTES = List.of(
            new Route("GET /api/orders", "/api/orders", SIGNED_IN),
            new Route("POST /api/orders", "/api/orders", SIGNED_IN),
            new Route("DELETE /api/admin/orders/{id}", "/api/admin/orders/O-1", Set.of("admin")),
            new Route("GET /api/audit", "/api/audit", Set.of("auditor")));

    @Autowired
    MockMvcTester mvc;

    @Autowired
    Personas personas;

    @Autowired
    @Qualifier("requestMappingHandlerMapping")
    RequestMappingHandlerMapping mappings;

    @Test
    void everyRouteIsListed() {
        Set<String> routes = new TreeSet<>();
        mappings.getHandlerMethods().forEach((info, handler) -> {
            if (handler.getBeanType().getPackageName().startsWith(getClass().getPackageName())) {
                info.getPatternValues().forEach(pattern -> info.getMethodsCondition().getMethods()
                        .forEach(method -> routes.add(method + " " + pattern)));
            }
        });
        routes.removeAll(ROUTES.stream().map(Route::route).toList());
        assertThat(routes).as("Routes missing from RouteAccessTests.ROUTES. Decide who may call them").isEmpty();
    }

    static Stream<Arguments> callers() {
        return ROUTES.stream().flatMap(route -> Stream.concat(Stream.of("anonymous"), Personas.NAMES.stream())
                .map(caller -> Arguments.of(route.route(), route.uri(), caller, route.allowed())));
    }

    @ParameterizedTest(name = "{0} as {2}")
    @MethodSource("callers")
    void callerGetsTheAccessListed(String route, String uri, String caller, Set<String> allowed) {
        var request = mvc.method(HttpMethod.valueOf(route.substring(0, route.indexOf(' ')))).uri(uri).with(csrf());
        boolean anonymous = caller.equals("anonymous");
        if (!anonymous) {
            request = request.with(personas.as(caller));
        }
        int status = request.exchange().getResponse().getStatus();
        if (allowed.contains(caller) || (!anonymous && allowed.contains("*"))) {
            assertThat(status).as("%s as %s should get through", route, caller).isNotIn(401, 302, 403);
        } else if (anonymous) {
            assertThat(status).as("%s as %s should have to log in", route, caller).isIn(401, 302);
        } else {
            assertThat(status).as("%s as %s should be refused", route, caller).isEqualTo(403);
        }
    }
}
