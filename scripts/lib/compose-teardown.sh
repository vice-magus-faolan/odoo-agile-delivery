#!/usr/bin/env bash
# Source after defining the run-owned COMPOSE_PROJECT_NAME and COMPOSE array.

cleanup_verification_resources() {
    local status=$? failed=0 kind flags resources filter="label=com.docker.compose.project=$COMPOSE_PROJECT_NAME"
    trap - EXIT INT TERM
    "${COMPOSE[@]}" down --volumes --remove-orphans || failed=1
    for kind in container volume network; do
        flags=-q; if [[ $kind == container ]]; then flags=-aq; fi
        if ! resources=$(docker "$kind" ls "$flags" --filter "$filter"); then
            printf 'Verification %s absence query failed: %s\n' "$kind" "$COMPOSE_PROJECT_NAME" >&2
            failed=1
        elif [[ -n $resources ]]; then
            printf 'Verification %s resources remain for %s:\n%s\n' "$kind" "$COMPOSE_PROJECT_NAME" "$resources" >&2
            failed=1
        fi
    done
    if (( failed )); then
        printf 'Verification teardown failed; original verification status: %s\n' "$status" >&2
        (( status != 0 )) || status=1
    else printf 'Verification teardown complete: %s (no containers, volumes or networks)\n' "$COMPOSE_PROJECT_NAME" >&2; fi
    exit "$status"
}

printf 'Owning fresh disposable verification project: %s\n' "$COMPOSE_PROJECT_NAME"
trap cleanup_verification_resources EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
