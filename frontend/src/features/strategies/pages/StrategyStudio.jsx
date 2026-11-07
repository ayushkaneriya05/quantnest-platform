import { useCallback, useEffect, useRef, useState } from "react";
import { useBlocker, useParams } from "react-router-dom";
import { Check, ChevronLeft, ChevronRight, Save } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { TabBar, TabButton } from "@/shared/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/shared/components/ui/dialog";
import { GlobalLoader } from "@/shared/components/ui/global-loader";
import { useNotifications } from "@/shared/hooks/useNotifications";
import { useStrategySpecification } from "@/shared/context/EnumsContext";
import { usePageActions } from "@/shared/context/pageActions";
import {
  getApiErrorDetails,
  getApiErrorMessage,
} from "@/shared/utils/apiErrors";
import { customConfirm } from "@/shared/components/ui/custom-dialog";
import { strategyApi } from "@/shared/services/strategyApi";
import StrategyConfiguration from "@/shared/components/StrategyConfiguration";
import StrategyConfigNav from "../components/StrategyConfigNav";
import StudioMarkets from "../components/StudioMarkets";
import StudioConditions from "../components/StudioConditions";
import StudioSchedule from "../components/StudioSchedule";
import { scheduleIssues } from "../studioPresentation";


export default function StrategyStudio() {
  const { id } = useParams();
  const { notify } = useNotifications();
  const {
    spec, operators,
    loading: metadataLoading,
    error: metadataError,
    refreshEnums,
  } = useStrategySpecification();
  const { setPageHeader, setPageActions } = usePageActions();
  const [strategy, setStrategy] = useState(null);
  const [document, setDocument] = useState(null);
  const [saved, setSaved] = useState(null);
  const [revision, setRevision] = useState("");
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [step, setStep] = useState(0);
  const [ruleType, setRuleType] = useState("ENTRY");
  const [customDays, setCustomDays] = useState(false);
  const [validated, setValidated] = useState(false);
  const [error, setError] = useState("");
  const [issues, setIssues] = useState([]);
  const inFlight = useRef(false);
  const request = useRef(0);
  const scroll = useRef(null);
  const errorSummary = useRef(null);
  const incompleteDays = Boolean(
    customDays && document && !document.time_rule.trading_days.length,
  );
  const dirty =
    JSON.stringify(document) !== JSON.stringify(saved) || incompleteDays;
  const navigation = useBlocker(
    ({ currentLocation, nextLocation }) =>
      dirty && currentLocation.pathname !== nextLocation.pathname,
  );

  // Only this page owns draft persistence. Child editors change the same document.
  const load = useCallback(async () => {
    const sequence = ++request.current;
    setLoading(true);
    try {
      const [item, result] = await Promise.all([
        strategyApi.getById(id),
        strategyApi.getDefinition(id),
      ]);
      if (sequence !== request.current) return;
      setStrategy(item);
      setDocument(result.document);
      setSaved(result.document);
      setCustomDays(Boolean(result.document.time_rule.trading_days.length));
      setRevision(result.revision);
      setInstruments(result.instruments);
      setError("");
      setIssues([]);
      setValidated(false);
    } catch (failure) {
      if (sequence === request.current)
        setError(
          getApiErrorMessage(failure, "Could not load Strategy Studio."),
        );
    } finally {
      if (sequence === request.current) setLoading(false);
    }
  }, [id]);
  useEffect(() => {
    load();
    return () => {
      request.current += 1;
    };
  }, [load]);
  useEffect(() => {
    if (!dirty) return;
    // Refresh/close is browser-owned; asynchronous custom dialogs cannot block it.
    // In-app navigation and Reload saved version use our themed dialogs below.
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const edit = (next) => {
    if (inFlight.current) return;
    setDocument(next);
    setValidated(false);
    setError("");
    setIssues([]);
  };
  const changeStep = useCallback((next) => {
    setStep(next);
    requestAnimationFrame(() => {
      scroll.current?.scrollTo({ top: 0 });
      scroll.current
        ?.querySelector(`[data-studio-step="${next}"]`)
        ?.focus({ preventScroll: true });
    });
  }, []);
  const reveal = (issue) => {
    changeStep(issue.step);
    requestAnimationFrame(() => {
      const target = scroll.current?.querySelector(issue.selector);
      if (!target) return;
      let parent = target.parentElement;
      while (parent && parent !== scroll.current) {
        if (parent.tagName === "DETAILS") parent.open = true;
        parent = parent.parentElement;
      }
      target.scrollIntoView({ block: "center" });
      target.focus({ preventScroll: true });
    });
  };
  const validate = useCallback(
    async (save) => {
      // A ref prevents duplicate submissions before React has rendered disabled controls.
      if (inFlight.current || !document) return;
      const local = scheduleIssues(document.time_rule, customDays);
      setIssues(local);
      setError("");
      if (local.length) {
        requestAnimationFrame(() => errorSummary.current?.focus());
        return;
      }
      inFlight.current = true;
      setBusy(save ? "Saving" : "Validating");
      const sequence = request.current;
      try {
        const result = save
          ? await strategyApi.saveDefinition(id, document, revision)
          : await strategyApi.validateDefinition(id, document);
        if (sequence !== request.current) return;
        setValidated(true);
        if (save) {
          setDocument(result.document);
          setSaved(result.document);
          setRevision(result.revision);
          setCustomDays(Boolean(result.document.time_rule.trading_days.length));
          notify.success(
            "Strategy version saved. Running sessions keep their deployed version.",
          );
        } else notify.success("Strategy conditions are valid.");
      } catch (failure) {
        if (sequence !== request.current) return;
        setValidated(false);
        setError(
          getApiErrorMessage(failure, "Could not validate the strategy."),
        );
        // Link only known structured field errors, never infer a location from prose.
        const timing = getApiErrorDetails(failure)?.time_rule;
        if (timing && typeof timing === "object")
          setIssues(
            Object.entries(timing)
              .filter(([key]) =>
                ["end_time", "start_time", "trading_days"].includes(key),
              )
              .map(([key, message]) => ({
                step: 2,
                selector:
                  key === "trading_days"
                    ? "[data-schedule-days]"
                    : `#studio-entry-${key === "start_time" ? "start" : "end"}`,
                message: Array.isArray(message)
                  ? message.join(" ")
                  : String(message),
              })),
          );
        requestAnimationFrame(() => errorSummary.current?.focus());
      } finally {
        inFlight.current = false;
        if (sequence === request.current) setBusy("");
      }
    },
    [customDays, document, id, notify, revision],
  );

  useEffect(() => {
    setPageHeader(<StrategyConfigNav strategy={strategy} />);
    setPageActions(
      document && !loading && !metadataLoading && !metadataError ? (
        <div className="studio-toolbar">
          <span className="studio-save-state" role="status">
            {busy || (dirty ? "Unsaved changes" : "Saved")}
            {validated && !busy ? " · Validated" : ""}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={Boolean(busy)}
            onClick={() => validate(false)}
          >
            <Check className="mr-1.5 h-4 w-4" />
            Validate
          </Button>
          <Button
            size="sm"
            disabled={Boolean(busy) || !dirty}
            onClick={() => validate(true)}
          >
            <Save className="mr-1.5 h-4 w-4" />
            Save version
          </Button>
        </div>
      ) : null,
    );
    return () => {
      setPageHeader(null);
      setPageActions(null);
    };
  }, [
    strategy,
    metadataLoading,
    metadataError,
    document,
    loading,
    busy,
    dirty,
    validated,
    validate,
    setPageHeader,
    setPageActions,
  ]);

  if (loading || metadataLoading)
    return <GlobalLoader text="Loading Strategy Studio…" />;
  if (metadataError)
    return (
      <div className="p-3">
        <p role="alert" className="text-destructive">
          Could not load builder choices.
        </p>
        <Button className="mt-3" onClick={refreshEnums}>
          Retry builder choices
        </Button>
      </div>
    );
  if (!document)
    return (
      <div className="p-3">
        <p role="alert" className="text-destructive">
          {error}
        </p>
        <Button onClick={load} className="mt-3">
          Retry
        </Button>
      </div>
    );
  const editorOperators = { ...operators, formulas: document.expressions };
  return (
    <div className="strategy-studio">
      <Dialog
        open={navigation.state === "blocked"}
        onOpenChange={(open) => {
          if (!open && navigation.state === "blocked") navigation.reset();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dirty ? "Leave unsaved changes?" : "Leave Strategy Studio?"}
            </DialogTitle>
            <DialogDescription>
              {dirty
                ? "Your changes are only in this draft. Save a version before leaving to keep them."
                : "Your version has finished saving. You can leave safely."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => navigation.reset()}>
              Keep editing
            </Button>
            <Button
              variant="destructive"
              disabled={Boolean(busy)}
              onClick={() => {
                setDocument(saved);
                setCustomDays(Boolean(saved.time_rule.trading_days.length));
                navigation.proceed();
              }}
            >
              {dirty ? "Discard and leave" : "Leave"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <TabBar className="studio-steps" role="navigation" aria-label="Strategy builder steps">
        {spec.steps.map((label, index) => (
          <TabButton active={step === index}
            key={label}
            type="button"
            aria-current={step === index ? "step" : undefined}
            onClick={() => changeStep(index)}
          >
            <span className="studio-step-number">{index + 1}</span>
            {label}
          </TabButton>
        ))}
      </TabBar>
      <div ref={scroll} className="studio-scroll scrollbar-theme">
        {(error || issues.length > 0) && (
          <div
            ref={errorSummary}
            tabIndex={-1}
            role="alert"
            className="studio-errors"
          >
            <strong>Check your strategy</strong>
            {error && <p className="mt-1">{error}</p>}
            {issues.length > 0 && (
              <ul className="mt-2 space-y-1">
                {issues.map((issue) => (
                  <li key={issue.selector}>
                    <Button variant="ghost"
                      type="button"
                      className="block h-auto justify-start whitespace-normal p-0 text-left underline underline-offset-2"
                      onClick={() => reveal(issue)}
                    >
                      {issue.message}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            {error && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-2"
                disabled={Boolean(busy)}
                onClick={async () => {
                  if (
                    !dirty ||
                    (await customConfirm("Reload and discard unsaved changes?"))
                  )
                    load();
                }}
              >
                Reload saved version
              </Button>
            )}
          </div>
        )}
        <fieldset disabled={Boolean(busy)} className="min-w-0">
          {/* Keep local disclosure and picker state when moving between steps. */}
          <section
            hidden={step !== 0}
            data-studio-step="0"
            tabIndex={-1}
            aria-label="Markets and size"
            className="studio-step-content"
          >
            <StudioMarkets
              document={document}
              onChange={edit}
              operators={editorOperators}
              instruments={instruments}
            />
          </section>
          <section
            hidden={step !== 1}
            data-studio-step="1"
            tabIndex={-1}
            aria-label="Conditions"
            className="studio-step-content"
          >
            <StudioConditions
              document={document}
              onChange={edit}
              operators={editorOperators}
              ruleType={ruleType}
              onRuleTypeChange={setRuleType}
            />
          </section>
          <section
            hidden={step !== 2}
            data-studio-step="2"
            tabIndex={-1}
            aria-label="Schedule"
            className="studio-step-content"
          >
            <StudioSchedule
              value={document.time_rule}
              onChange={(time_rule) => edit({ ...document, time_rule })}
              customDays={customDays}
              onCustomDaysChange={(next) => {
                if (!inFlight.current) {
                  setCustomDays(next);
                  setValidated(false);
                }
              }}
              issues={issues}
            />
          </section>
          <section
            hidden={step !== 3}
            data-studio-step="3"
            tabIndex={-1}
            aria-label="Review"
            className="studio-step-content"
          >
            <StrategyConfiguration
              snapshot={{
                name: strategy.name,
                description: strategy.description,
                ...document,
              }}
              onEditSection={changeStep}
            />
          </section>
        </fieldset>
      </div>
      <footer className="studio-footer">
        <Button
          variant="ghost"
          size="sm"
          disabled={step === 0}
          onClick={() => changeStep(step - 1)}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Previous
        </Button>
        <span className="studio-footer-progress text-xs text-muted-foreground">
          Step {step + 1} of {spec.steps.length}
        </span>
        {step < spec.steps.length - 1 ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => changeStep(step + 1)}
          >
            Next: {spec.steps[step + 1]}
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        ) : (
          <span className="text-xs text-muted-foreground">
            Save from the toolbar
          </span>
        )}
      </footer>
    </div>
  );
}
