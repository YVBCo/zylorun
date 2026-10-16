import { useState } from 'react';
import {
  HelpCircle,
  X,
  Search,
  AlertTriangle,
  Info,
} from 'lucide-react';
import {
  TABS_EXPLANATIONS,
  ANALYZERS_EXPLANATIONS,
  CONTROLS_EXPLANATIONS,
} from '../data/featureCatalogue';
import type {
  TabExplanation,
  AnalyzerExplanation,
  ControlExplanation,
} from '../data/featureCatalogue';

interface FeatureExplainerModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTabId?: string;
}

export default function FeatureExplainerModal({
  isOpen,
  onClose,
  initialTabId,
}: FeatureExplainerModalProps) {
  const [section, setSection] = useState<'tabs' | 'analyzers' | 'controls'>('tabs');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState<string>(initialTabId || 'overview');

  if (!isOpen) return null;

  const filteredTabs = Object.values(TABS_EXPLANATIONS).filter(
    (t) =>
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.purpose.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredAnalyzers = Object.values(ANALYZERS_EXPLANATIONS).filter(
    (a) =>
      a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.purpose.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredControls = Object.values(CONTROLS_EXPLANATIONS).filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.shortHelp.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-100">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Zylorun Project Hub Feature Guide & Verification Catalogue
              </h2>
              <p className="text-xs text-slate-400">
                Verified, maintainable user guide for all 9 intelligence tabs, 10 continuous analyzers, and key metrics.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Section Navigation & Search */}
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/50">
          <div className="flex space-x-2 w-full sm:w-auto">
            <button
              onClick={() => {
                setSection('tabs');
                setSelectedItem('overview');
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                section === 'tabs'
                  ? 'bg-brand-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              Hub Tabs (9)
            </button>
            <button
              onClick={() => {
                setSection('analyzers');
                setSelectedItem('repository_dna');
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                section === 'analyzers'
                  ? 'bg-brand-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              Analyzers Suite (10)
            </button>
            <button
              onClick={() => {
                setSection('controls');
                setSelectedItem('risk_score');
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                section === 'controls'
                  ? 'bg-brand-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              Controls & Metrics
            </button>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search features..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        {/* Modal Body: Left Sidebar + Right Details */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-800">
          {/* Left Selection List */}
          <div className="p-3 overflow-y-auto max-h-[55vh] md:max-h-none space-y-1">
            {section === 'tabs' &&
              filteredTabs.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelectedItem(t.id)}
                  className={`w-full text-left p-2.5 rounded-xl text-xs transition flex flex-col gap-0.5 ${
                    selectedItem === t.id
                      ? 'bg-brand-500/10 text-brand-300 border border-brand-500/30'
                      : 'text-slate-300 hover:bg-slate-800/60'
                  }`}
                >
                  <span className="font-semibold text-white">{t.title}</span>
                  <span className="text-[11px] text-slate-400 truncate">{t.summary}</span>
                </button>
              ))}

            {section === 'analyzers' &&
              filteredAnalyzers.map((a) => (
                <button
                  key={a.id}
                  onClick={() => setSelectedItem(a.id)}
                  className={`w-full text-left p-2.5 rounded-xl text-xs transition flex flex-col gap-0.5 ${
                    selectedItem === a.id
                      ? 'bg-brand-500/10 text-brand-300 border border-brand-500/30'
                      : 'text-slate-300 hover:bg-slate-800/60'
                  }`}
                >
                  <span className="font-semibold text-white">{a.title}</span>
                  <span className="text-[11px] text-slate-400 truncate">{a.purpose}</span>
                </button>
              ))}

            {section === 'controls' &&
              filteredControls.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelectedItem(c.id)}
                  className={`w-full text-left p-2.5 rounded-xl text-xs transition flex flex-col gap-0.5 ${
                    selectedItem === c.id
                      ? 'bg-brand-500/10 text-brand-300 border border-brand-500/30'
                      : 'text-slate-300 hover:bg-slate-800/60'
                  }`}
                >
                  <span className="font-semibold text-white">{c.title}</span>
                  <span className="text-[11px] text-slate-400 truncate">{c.shortHelp}</span>
                </button>
              ))}
          </div>

          {/* Right Detail Pane */}
          <div className="md:col-span-2 p-6 overflow-y-auto space-y-4">
            {section === 'tabs' && (
              <TabDetailPane tab={TABS_EXPLANATIONS[selectedItem] || filteredTabs[0]} />
            )}
            {section === 'analyzers' && (
              <AnalyzerDetailPane analyzer={ANALYZERS_EXPLANATIONS[selectedItem] || filteredAnalyzers[0]} />
            )}
            {section === 'controls' && (
              <ControlDetailPane control={CONTROLS_EXPLANATIONS[selectedItem] || filteredControls[0]} />
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
          <span>
            Verification Engine: <b>Deterministic by Default</b> (No external AI keys required)
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium transition"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
}

function TabDetailPane({ tab }: { tab?: TabExplanation }) {
  if (!tab) return <div className="text-slate-500 text-sm">Select a tab from the list.</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-bold text-white">{tab.title}</h3>
          <p className="text-xs text-slate-400 mt-0.5">{tab.summary}</p>
        </div>
        <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          {tab.verificationType}
        </span>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-400">Purpose</h4>
        <p className="text-xs text-slate-300 leading-relaxed">{tab.purpose}</p>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-400">Why Use It</h4>
        <p className="text-xs text-slate-300 leading-relaxed">{tab.whyUseIt}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
          <h5 className="text-[11px] font-bold text-slate-400 uppercase">Input Data</h5>
          <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
            {tab.inputsUsed.map((inp, idx) => (
              <li key={idx}>{inp}</li>
            ))}
          </ul>
        </div>
        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
          <h5 className="text-[11px] font-bold text-slate-400 uppercase">Outputs Provided</h5>
          <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
            {tab.outputsProvided.map((out, idx) => (
              <li key={idx}>{out}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-400">How to Interpret Results</h4>
        <p className="text-xs text-slate-300 leading-relaxed">{tab.howToInterpret}</p>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-400">Actions Available</h4>
        <div className="flex flex-wrap gap-1.5">
          {tab.actionsAvailable.map((act, idx) => (
            <span
              key={idx}
              className="text-[11px] px-2.5 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700"
            >
              {act}
            </span>
          ))}
        </div>
      </div>

      {tab.limitations && tab.limitations.length > 0 && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl space-y-1">
          <h5 className="text-[11px] font-bold text-amber-400 uppercase flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Known Limitations & Prerequisites
          </h5>
          <p className="text-xs text-amber-200/90 leading-relaxed">{tab.limitations[0]}</p>
        </div>
      )}
    </div>
  );
}

function AnalyzerDetailPane({ analyzer }: { analyzer?: AnalyzerExplanation }) {
  if (!analyzer) return <div className="text-slate-500 text-sm">Select an analyzer from the list.</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-bold text-white">{analyzer.title}</h3>
          <p className="text-xs text-slate-400 mt-0.5">{analyzer.purpose}</p>
        </div>
        <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
          Deterministic Rule Engine
        </span>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-400">Problems Detected</h4>
        <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
          {analyzer.problemsDetected.map((prob, idx) => (
            <li key={idx}>{prob}</li>
          ))}
        </ul>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
          <h5 className="text-[11px] font-bold text-slate-400 uppercase">When It Runs</h5>
          <p className="text-xs text-slate-300">{analyzer.whenItRuns}</p>
        </div>
        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
          <h5 className="text-[11px] font-bold text-slate-400 uppercase">Supported Files</h5>
          <p className="text-xs text-slate-300">{analyzer.supportedFiles.join(', ')}</p>
        </div>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-400">Evidence Produced</h4>
        <p className="text-xs text-slate-300 leading-relaxed">{analyzer.evidenceProduced}</p>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-400">Underlying Tools Executed</h4>
        <div className="flex flex-wrap gap-1.5">
          {analyzer.toolsExecuted.map((tool, idx) => (
            <span
              key={idx}
              className="text-[11px] px-2.5 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700"
            >
              {tool}
            </span>
          ))}
        </div>
      </div>

      <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
        <h5 className="text-[11px] font-bold text-slate-400 uppercase flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-slate-400" />
          What It Cannot Verify (Boundary Disclosure)
        </h5>
        <p className="text-xs text-slate-300 leading-relaxed">{analyzer.whatItCannotVerify}</p>
      </div>
    </div>
  );
}

function ControlDetailPane({ control }: { control?: ControlExplanation }) {
  if (!control) return <div className="text-slate-500 text-sm">Select a control from the list.</div>;

  return (
    <div className="space-y-4">
      <div className="border-b border-slate-800 pb-3">
        <h3 className="text-base font-bold text-white">{control.title}</h3>
        <p className="text-xs text-slate-400 mt-0.5">{control.shortHelp}</p>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-400">Technical Details</h4>
        <p className="text-xs text-slate-300 leading-relaxed">{control.details}</p>
      </div>

      <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
        <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">How to Interpret</h4>
        <p className="text-xs text-slate-200 leading-relaxed">{control.interpretation}</p>
      </div>
    </div>
  );
}
