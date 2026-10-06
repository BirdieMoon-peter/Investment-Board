"""Explicit experiment-only frozen research through the existing configured provider."""
from app.services.research_service import build_configured_provider, audit
from app.services.providers.research_provider import ResearchProviderError, PROMPT_VERSION
from app.schemas.research import ResearchOutput, CritiqueOutput
from app.db.models.quant import QuantRun
from app.db.repositories.quant_repository import canonical, fingerprint
import json


def frozen_snapshot(run):
    payload = json.loads(run.payload_json)
    metrics = []
    for segment, values in [('full', payload['result']['metrics']), ('baseline', payload['baseline']['metrics']), ('holdout', payload['holdout']['result']['metrics'])]:
        for key, value in values.items():
            if key == 'sample_count':
                value = str(value)
            metrics.append({'key': segment + '.' + key, 'value': value, 'status': 'ready' if value is not None else 'unavailable', 'unit': 'CNY' if key in {'end_nav', 'fees_paid'} else 'count' if key == 'sample_count' else 'ratio', 'as_of': payload['result']['equity'][-1]['date']})
    ledger = [{'evidence_id': 'experiment:' + str(run.id), 'kind': 'frozen_deterministic_experiment', 'title_only': False, 'content': 'Frozen deterministic rules, costs, chronological holdout and assumptions; no optimized alpha or verified total-return claim.', 'strategy': payload['strategy'], 'assumptions': payload['assumptions'], 'warnings': payload['warnings']}, {'evidence_id': 'robustness:' + str(run.id), 'kind': 'frozen_robustness', 'title_only': False, 'content': 'Same held-out segment parameter-neighbor and doubled-cost diagnostics.', 'diagnostics': payload['robustness']}]
    snapshot = {'scope': 'frozen_experiment_only_no_actual_holdings', 'run_id': run.id, 'run_fingerprint': run.fingerprint, 'dataset_fingerprint': payload['dataset_fingerprint'], 'strategy_fingerprint': payload['strategy_fingerprint'], 'metrics': metrics, 'ledger': ledger, 'authoritative': 'deterministic_metrics', 'ai_label': 'model_inference_not_trading_signal_or_verification'}
    return json.loads(canonical(snapshot))


def generate(service, run_id, critique=False):
    run = service.repo.require(QuantRun, run_id)
    frozen = frozen_snapshot(run); raw = canonical(frozen)
    model = 'unavailable'
    try:
        provider = (service.provider_factory or build_configured_provider)()
        model = provider.model_name
        output = ResearchOutput.model_validate(provider.generate(json.loads(raw))).model_dump(mode='json')
        diagnostics = audit(json.loads(raw), output)
        review = {'status': 'not_requested', 'label': 'model_review_not_verification'}
        if critique:
            try:
                evaluated = CritiqueOutput.model_validate(provider.critique(json.loads(raw), json.loads(canonical(output)))).model_dump(mode='json')
                if any(item['claim_index'] >= len(output['claims']) for item in evaluated['claims']):
                    raise ValueError('invalid critique index')
                review = {'status': 'available', 'label': 'model_review_not_verification', **evaluated}
            except Exception:
                review = {'status': 'unavailable', 'label': 'model_review_not_verification'}
        result = {'status': 'completed', 'research': output, 'diagnostics': diagnostics, 'model_review': review}
    except ResearchProviderError as exc:
        result = {'status': 'failed', 'error_code': exc.code}
    except Exception:
        result = {'status': 'failed', 'error_code': 'invalid_output'}
    result.update(input_snapshot=json.loads(raw), input_fingerprint=fingerprint(raw), model_name=model, prompt_version=PROMPT_VERSION, ai_label='model_inference_not_trading_signal_or_verification')
    return service.repo.annotate(run_id, 'research', result)
