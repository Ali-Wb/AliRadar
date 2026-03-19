const listeners = new Set();

const state = {
  rules: [],
  events: [],
};

function notify() {
  listeners.forEach((listener) => listener());
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot() {
  return {
    rules: [...state.rules],
    events: [...state.events],
  };
}

export function setRules(rules) {
  state.rules = [...(rules || [])];
  notify();
}

export function addEvent(event) {
  state.events = [event, ...state.events].slice(0, 50);
  notify();
}

export function setEvents(events) {
  state.events = [...(events || [])].slice(0, 50);
  notify();
}
