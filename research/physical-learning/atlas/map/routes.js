// Stable public node IDs refer to the synchronized SFP research graph.
export const routes = {
  cost: {
    title: 'The price of preparation',
    steps: [
      ['Start with', 'Two matching responses', 'Two resistor ladders agree in their present response and in how they initially respond to training.'],
      ['Ask', 'How quickly can each change?', 'Require both to make the same small increase in a learning response while preserving the protected output.'],
      ['Find', 'Two different time scales', 'Even with the same bound on the controls, one state can reach the target faster.']
    ],
    cases: [
      ['af0ba032a378a7','Compare the time scales','For a small target increment δ and control bound U, the minimum times scale as δ¹ᐟ³/U and √δ/U. The square-root route is faster for sufficiently small δ.','This comparison concerns one protected change in a positive resistor ladder.'],
      ['9048ed888925ad','Count the cost of switching','Moving to the state with the faster next operation also takes time. A faster operation alone does not establish a saving for the whole sequence.','The switching result concerns a particular pair of states.'],
      ['839eda0b274186','Extend the ladder','The distinction between the two cost regimes survives the addition of a fixed, sufficiently conductive input section, even when its new edges can learn.','The extension is finite. The result does not cover arbitrary loads.']
    ]
  },
  learning: {
    title: 'Learning after a change',
    steps: [
      ['Start with','Recover a function','Training changes internal parameters. A network can later recover its earlier input–output function.'],
      ['Ask','What did the network retain?','Apply a future learning task and compare the responses.'],
      ['Examine','Equivalence under future training','The manuscript identifies when internal changes remain invisible to future tasks in a specified linear model.']
    ],
    cases:[['65ee750f5172f5','Inspect the equivalence condition','For the reversible square two-layer linear network studied here, matching the current function and the specified parameters still leaves a learning-response operator to compare. Equality of that operator characterizes future equivalence under the stated assumptions.','The equivalence condition is specific to this model.']]
  },
  observation: {
    title: 'Access through observation',
    steps: [
      ['Start with','A fast physical route','Different internal states can permit different routes to preparation.'],
      ['Ask','Can the controller tell them apart?','Compare the output signals available before choosing an action.'],
      ['Find','A distinction at third order','In the five-cell example, observations through second order coincide even as the fast action changes.']
    ],
    cases:[['0601027dfa12ba','Inspect the observation limit','The third-order output distinguishes states that lower-order observations leave indistinguishable in this family.','The example concerns a local regime in a five-cell network.']]
  }
};
