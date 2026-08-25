package {{PACKAGE}}.{{MODULE}}.domain;

import {{PACKAGE}}.{{MODULE}}.domain.vo.*;
import {{PACKAGE}}.{{MODULE}}.domain.models.{{NAME}}VM;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * CQRS Service templates - separate write and read operations.
 *
 * {{NAME}}Service - Write operations (commands), @Transactional
 * {{NAME}}QueryService - Read operations (queries), @Transactional(readOnly = true)
 */

// ============================================================
// WRITE SERVICE - Commands, state changes
// ------------------------------------------------------------
// NOTE: this bundle template shows two services in one file for
// readability. Java only allows one `public` top-level type per
// source file, so both services are package-private (no `public`
// modifier) — same convention as controller.java / repository.java.
// If you need them to be `public`, split each class into its own
// .java file before applying.
// ============================================================

@Service
@Transactional
class {{NAME}}Service {
    private final {{NAME}}Repository repository;
    private final ApplicationEventPublisher eventPublisher;

    {{NAME}}Service({{NAME}}Repository repository, ApplicationEventPublisher eventPublisher) {
        this.repository = repository;
        this.eventPublisher = eventPublisher;
    }

    public {{NAME}}Code create(Create{{NAME}}Cmd cmd) {
        var entity = {{NAME}}Entity.create(cmd.details());
        repository.save(entity);

        eventPublisher.publishEvent(new {{NAME}}Created(
            entity.getCode().code(),
            entity.getDetails().name()
        ));

        return entity.getCode();
    }

    public void activate({{NAME}}Code code) {
        var entity = repository.getByCode(code);
        entity.activate();
        repository.save(entity);

        eventPublisher.publishEvent(new {{NAME}}Activated(code.code()));
    }

    public void deactivate({{NAME}}Code code) {
        var entity = repository.getByCode(code);
        entity.deactivate();
        repository.save(entity);
    }
}

// ============================================================
// READ SERVICE - Queries, no state changes
// ============================================================

@Service
@Transactional(readOnly = true)
class {{NAME}}QueryService {
    private final {{NAME}}Repository repository;
    private final {{NAME}}Mapper mapper;

    {{NAME}}QueryService({{NAME}}Repository repository, {{NAME}}Mapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    public List<{{NAME}}VM> findAll() {
        return repository.findAll()
            .stream()
            .map(mapper::toVM)
            .toList();
    }

    public List<{{NAME}}VM> findAllActive() {
        return repository.findAllActive()
            .stream()
            .map(mapper::toVM)
            .toList();
    }

    public {{NAME}}VM getByCode({{NAME}}Code code) {
        var entity = repository.getByCode(code);
        return mapper.toVM(entity);
    }
}

// ============================================================
// MAPPER - Entity to ViewModel
// ============================================================

@Component
class {{NAME}}Mapper {
    {{NAME}}VM toVM({{NAME}}Entity entity) {
        return new {{NAME}}VM(
            entity.getId().id(),
            entity.getCode().code(),
            entity.getDetails().name(),
            entity.getDetails().description(),
            entity.getStatus().name(),
            entity.getCreatedAt(),
            entity.getUpdatedAt()
        );
    }
}

// ============================================================
// COMMAND - Input for write operations
// ============================================================

// public record Create{{NAME}}Cmd(
//     {{NAME}}Details details
// ) {}

// ============================================================
// VIEW MODEL - Output for read operations (primitives only)
// ============================================================

// public record {{NAME}}VM(
//     Long id,
//     String code,
//     String name,
//     String description,
//     String status,
//     Instant createdAt,
//     Instant updatedAt
// ) {}
