package {{PACKAGE}}.{{MODULE}}.rest;

import {{PACKAGE}}.{{MODULE}}.domain.*;
import {{PACKAGE}}.{{MODULE}}.domain.models.{{NAME}}VM;
import {{PACKAGE}}.{{MODULE}}.domain.vo.{{NAME}}Code;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

import static org.springframework.http.HttpStatus.CREATED;

/**
 * REST Controller template.
 *
 * Key principles:
 * - Use Value Objects in @PathVariable (requires Spring Converter)
 * - Validate with @Valid
 * - Delegate to services - no business logic here
 * - Return appropriate HTTP status codes
 */
@RestController
@RequestMapping("/api/{{MODULE}}")
class {{NAME}}Controller {
    private final {{NAME}}Service service;
    private final {{NAME}}QueryService queryService;

    {{NAME}}Controller({{NAME}}Service service, {{NAME}}QueryService queryService) {
        this.service = service;
        this.queryService = queryService;
    }

    // ==================== READ OPERATIONS ====================

    @GetMapping
    List<{{NAME}}VM> findAll() {
        return queryService.findAll();
    }

    @GetMapping("/active")
    List<{{NAME}}VM> findAllActive() {
        return queryService.findAllActive();
    }

    @GetMapping("/{code}")
    ResponseEntity<{{NAME}}VM> findByCode(@PathVariable {{NAME}}Code code) {
        return ResponseEntity.ok(queryService.getByCode(code));
    }

    // ==================== WRITE OPERATIONS ====================

    @PostMapping
    ResponseEntity<Create{{NAME}}Response> create(@RequestBody @Valid Create{{NAME}}Request request) {
        var cmd = new Create{{NAME}}Cmd(request.details());
        var code = service.create(cmd);
        return ResponseEntity.status(CREATED).body(new Create{{NAME}}Response(code.code()));
    }

    @PatchMapping("/{code}/activate")
    ResponseEntity<Void> activate(@PathVariable {{NAME}}Code code) {
        service.activate(code);
        return ResponseEntity.ok().build();
    }

    @PatchMapping("/{code}/deactivate")
    ResponseEntity<Void> deactivate(@PathVariable {{NAME}}Code code) {
        service.deactivate(code);
        return ResponseEntity.ok().build();
    }
}

// ============================================================
// REQUEST/RESPONSE DTOs
// ============================================================

// public record Create{{NAME}}Request(
//     @Valid {{NAME}}Details details
// ) {}

// public record Create{{NAME}}Response(String code) {}

// ============================================================
// SPRING CONVERTER - For @PathVariable binding
// ============================================================

// package {{PACKAGE}}.{{MODULE}}.rest.converters;
//
// @Component
// public class StringTo{{NAME}}CodeConverter implements Converter<String, {{NAME}}Code> {
//     @Override
//     public {{NAME}}Code convert(String source) {
//         return {{NAME}}Code.of(source);
//     }
// }
