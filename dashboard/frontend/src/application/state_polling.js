feature.statePolling = (function () {
  const POLL_INTERVAL_MS = 5000;

  function isCurrentRequest(generation, activeGeneration, requestSelection, selection) {
    return (
      generation === activeGeneration &&
      feature.domain.sameSelection(requestSelection, selection)
    );
  }

  function acceptStateSuccess(current, request, activeRequest, raw) {
    if (
      !isCurrentRequest(
        request.generation,
        activeRequest.generation,
        request.selection,
        activeRequest.selection
      )
    ) {
      return current;
    }
    const response = feature.domain.normalizeResponse(raw);
    if (
      response.available &&
      current.response &&
      current.response.available &&
      feature.domain.sameSelection(current.responseSelection, request.selection) &&
      response.state.revision < current.response.state.revision
    ) {
      return current;
    }
    return {
      response: response,
      responseSelection: request.selection,
      selectedStateError:
        request.selection.mode === "exact" && !response.available
          ? { kind: "unavailable" }
          : null,
      errorSelection:
        request.selection.mode === "exact" && !response.available ? request.selection : null,
      hasError: false,
    };
  }

  function acceptStateFailure(current, request, activeRequest) {
    if (
      !isCurrentRequest(
        request.generation,
        activeRequest.generation,
        request.selection,
        activeRequest.selection
      )
    ) {
      return current;
    }
    return {
      response: current.response,
      responseSelection: current.responseSelection,
      selectedStateError:
        request.selection.mode === "exact" ? { kind: "unavailable" } : null,
      errorSelection: request.selection,
      hasError: request.selection.mode !== "exact",
    };
  }

  function deriveStateView(current, selection, loading) {
    const matches =
      current.response &&
      current.response.available === true &&
      feature.domain.sameSelection(current.responseSelection, selection);
    const hasActiveError =
      current.selectedStateError &&
      feature.domain.sameSelection(current.errorSelection, selection);
    return {
      hasMatchingResponse: Boolean(matches && !hasActiveError),
      selectedStateError: hasActiveError ? current.selectedStateError : null,
      hasError: Boolean(current.hasError && selection.mode === "latest" && !hasActiveError),
      selectedStateLoading: Boolean(
        !hasActiveError &&
          (loading ||
            (selection.mode === "exact" && !matches) ||
            (selection.mode === "latest" && current.response && current.response.available && !matches))
      ),
    };
  }

  function shouldPollImmediately(selection, mounted) {
    return selection.mode === "exact" || mounted;
  }

  function useSelectedState(initialResponse, selection) {
    const initialState = {
      response: initialResponse,
      responseSelection: feature.domain.latestSelection(),
      selectedStateError: null,
      errorSelection: null,
      hasError: false,
    };
    const statePair = SDK.hooks.useState(initialState);
    const state = statePair[0];
    const setState = statePair[1];
    const loadingPair = SDK.hooks.useState(false);
    const loading = loadingPair[0];
    const setLoading = loadingPair[1];
    const generationRef = SDK.hooks.useRef(0);
    const mountedRef = SDK.hooks.useRef(false);
    const refreshRef = SDK.hooks.useRef(null);

    SDK.hooks.useEffect(
      function () {
        let cancelled = false;
        let timer = null;
        let inFlight = false;
        let refreshAfterCurrentPoll = false;
        let queuedRefreshWaiters = [];
        const request = {
          generation: generationRef.current + 1,
          selection: selection,
        };
        generationRef.current = request.generation;
        const activeRequest = request;
        const pollImmediately = shouldPollImmediately(request.selection, mountedRef.current);
        mountedRef.current = true;
        setLoading(pollImmediately);
        setState(function (current) {
          return { ...current, selectedStateError: null, errorSelection: null, hasError: false };
        });

        async function poll() {
          inFlight = true;
          try {
            const raw = await feature.infrastructure.loadState(request.selection);
            if (!cancelled && request.generation === generationRef.current) {
              setState(function (current) {
                return acceptStateSuccess(current, request, activeRequest, raw);
              });
            }
          } catch (_error) {
            if (!cancelled && request.generation === generationRef.current) {
              setState(function (current) {
                return acceptStateFailure(current, request, activeRequest);
              });
            }
          } finally {
            inFlight = false;
            if (!cancelled && request.generation === generationRef.current) {
              setLoading(false);
              if (timer !== null) window.clearTimeout(timer);
              if (refreshAfterCurrentPoll) {
                refreshAfterCurrentPoll = false;
                timer = null;
                const waiters = queuedRefreshWaiters;
                queuedRefreshWaiters = [];
                setLoading(true);
                poll().then(function () {
                  waiters.forEach(function (resolve) {
                    resolve();
                  });
                });
              } else {
                timer = window.setTimeout(poll, POLL_INTERVAL_MS);
              }
            }
          }
        }

        const refresh = function () {
          if (timer !== null) {
            window.clearTimeout(timer);
            timer = null;
          }
          if (inFlight) {
            refreshAfterCurrentPoll = true;
            return new Promise(function (resolve) {
              queuedRefreshWaiters.push(resolve);
            });
          }
          setLoading(true);
          return poll();
        };
        refreshRef.current = refresh;

        if (pollImmediately) {
          poll();
        } else {
          timer = window.setTimeout(poll, POLL_INTERVAL_MS);
        }
        return function () {
          cancelled = true;
          if (timer !== null) window.clearTimeout(timer);
          refreshAfterCurrentPoll = false;
          queuedRefreshWaiters.splice(0).forEach(function (resolve) {
            resolve();
          });
          if (refreshRef.current === refresh) refreshRef.current = null;
        };
      },
      [selection.mode, selection.profileId, selection.sessionId]
    );

    const view = deriveStateView(state, selection, loading);
    return {
      response: state.response,
      hasError: view.hasError,
      selectedStateError: view.selectedStateError,
      selectedStateLoading: view.selectedStateLoading,
      hasMatchingResponse: view.hasMatchingResponse,
      refreshNow: function () {
        return refreshRef.current ? refreshRef.current() : Promise.resolve();
      },
    };
  }

  return {
    isCurrentRequest: isCurrentRequest,
    acceptStateSuccess: acceptStateSuccess,
    acceptStateFailure: acceptStateFailure,
    deriveStateView: deriveStateView,
    shouldPollImmediately: shouldPollImmediately,
    useSelectedState: useSelectedState,
  };
})();
