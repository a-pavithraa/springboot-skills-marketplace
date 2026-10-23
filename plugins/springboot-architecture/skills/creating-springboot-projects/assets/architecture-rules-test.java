package {{PACKAGE}};

import com.enofex.taikai.Taikai;
import com.enofex.taikai.TaikaiRule;
import com.tngtech.archunit.core.domain.JavaModifier;
import org.junit.jupiter.api.Test;

import java.util.List;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

/**
 * Architecture rules that fail the build, so they hold whoever writes the code: a person, or an agent late in a
 * long session. Taikai 2.1.0 on ArchUnit 1.5 (test dependency com.enofex:taikai, see pom-additions.xml).
 * Runs without Docker.
 *
 * Verified on Spring Boot 4.1.1: each rule below was shown to fail on a planted violation, and none fired on
 * correct code. Two Taikai defaults needed fixing for Boot 4, marked below.
 *
 * progen projects already have ArchUnitTests.java with Taikai (names, package-private controllers, no
 * controller-to-controller calls, no @Autowired fields, logger convention, no generic throws, no import cycles,
 * no @Disabled tests). Add only the rules marked [beyond progen] to that file instead of creating this one, after
 * the three changes in references/progen-integration.md (progen pins Taikai 1.66.0, which has no jpa() rules).
 *
 * Per architecture style:
 * - layered: delete the entity and repository package-private rules (other layers' packages use them)
 * - package-by-module, tomato: as is
 * - modular monolith: as is, plus modularity-test.java (Spring Modulith verifies module boundaries; don't
 *   repeat those rules here)
 * - DDD+Hexagonal: services may be command handlers, so use namesShouldMatch(".+(Service|Handler)"), and add an
 *   ArchUnit onionArchitecture() rule (example in pom-additions.xml)
 */
class ArchitectureRulesTest {

    // Spring applies these through a proxy, so a call from inside the same class silently skips them: no
    // transaction, no retry, no cache, no security check. Taikai's default list has the old Spring Retry
    // annotation (org.springframework.retry), not Framework 7's native @Retryable, so list them all here.
    static final List<String> APPLIED_BY_PROXY = List.of(
            "org.springframework.transaction.annotation.Transactional",
            "jakarta.transaction.Transactional",
            "org.springframework.scheduling.annotation.Async",
            "org.springframework.cache.annotation.Cacheable",
            "org.springframework.cache.annotation.CacheEvict",
            "org.springframework.cache.annotation.CachePut",
            "org.springframework.security.access.prepost.PreAuthorize",
            "org.springframework.security.access.prepost.PostAuthorize",
            "org.springframework.resilience.annotation.Retryable",
            "org.springframework.resilience.annotation.ConcurrencyLimit");

    @Test
    void architecture() {
        Taikai.builder()
                .namespace("{{PACKAGE}}")
                .java(java -> java
                        .noUsageOfSystemOutOrErr()                                   // [beyond progen]
                        .methodsShouldNotDeclareGenericExceptions()
                        .imports(imports -> imports.shouldHaveNoCycles()))
                .spring(spring -> spring
                        .noAutowiredFields()
                        .noSelfInvocationOfProxiedMethods(APPLIED_BY_PROXY)          // [beyond progen]
                        .controllers(controllers -> controllers
                                .namesShouldEndWithController()
                                .shouldBePackagePrivate()
                                .shouldNotDependOnOtherControllers())
                        .services(services -> services
                                .namesShouldEndWithService()
                                .shouldNotDependOnControllers())
                        .repositories(repositories -> repositories
                                .namesShouldEndWithRepository()
                                .shouldNotDependOnServices())
                        .transactional(transactional -> transactional
                                .shouldNotBeUsedInControllers()))                    // [beyond progen]
                .jpa(jpa -> jpa.entities(entities -> entities
                        .shouldBePackagePrivate()                                    // [beyond progen] not for layered
                        .shouldHaveFieldAnnotatedWithVersion()))                     // [beyond progen]
                .logging(logging -> logging.loggersShouldFollowConventions("org.slf4j.Logger", "LOG",
                        List.of(JavaModifier.PRIVATE, JavaModifier.STATIC, JavaModifier.FINAL)))
                .test(test -> test.junit(junit -> junit
                        .classesShouldNotBeAnnotatedWithDisabled()
                        .methodsShouldNotBeAnnotatedWithDisabled()))
                // [beyond progen] Taikai's controllers().shouldNotDependOnRepositories() only sees classes annotated
                // @Repository, so it misses Spring Data interfaces (extends JpaRepository), the usual shortcut.
                .addRule(TaikaiRule.of(noClasses()
                        .that().areAnnotatedWith("org.springframework.web.bind.annotation.RestController")
                        .or().areAnnotatedWith("org.springframework.stereotype.Controller")
                        .should().dependOnClassesThat().areAssignableTo("org.springframework.data.repository.Repository")
                        .as("Controllers should not use Spring Data repositories directly")))
                .build()
                .checkAll();
    }
}

// Left out on purpose:
// - test().junit().methodsShouldContainAssertionsOrVerifications(): recognises only JUnit, AssertJ, Hamcrest,
//   Mockito verify and MockMvc andExpect. It flagged tests that assert through RestTestClient expectBody() and
//   WireMock verify() (writing-springboot-tests templates) as asserting nothing.
// - transactional().methodsShouldBePublic(): since Framework 6, class-based proxies apply @Transactional to
//   protected and package-private methods too.
// - repositories().shouldBePackagePrivate(): Taikai checks only @Repository classes; repository.java is already
//   package-private in package-by-module layouts.
