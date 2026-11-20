export const routes = {
  existence: {
    title:'Where can organization arise?',
    steps:[
      ['Look for','A local state','Identify a bounded part of the system that changes as its surroundings evolve.'],
      ['Ask','What does it organize later?','Compare how the later process unfolds when that local state differs.'],
      ['Distinguish','Origin and execution','A state can influence a later process even when its own formation remains unexplained.']
    ],
    cases:[['32d833f348ce37','Inspect the existence question','Which physical systems can produce a local organizing state through their own dynamics?','A construction in a mathematical model establishes possibility under its assumptions. A physical example requires separate evidence.']]
  },
  limits: {
    title:'Where is formation impossible?',
    steps:[
      ['Specify','A class of systems','Fix the local rules, admissible states and resources.'],
      ['Ask','Which organizations are out of reach?','Identify the restriction that could rule out a later organization.'],
      ['Test','The boundary of the claim','Check whether the restriction holds throughout the proposed class.']
    ],
    cases:[['8845886be6cbcf','Inspect the impossibility question','Under which explicit restrictions can the formation of an organizing state be ruled out?','An unsuccessful search for examples leaves the impossibility question open.']]
  },
  conditions: {
    title:'What sets the boundary?',
    steps:[
      ['Vary','A condition of the model','In a random partial order, the chance of a direct link can depend on the time gap between two events.'],
      ['Ask','Can the earlier event reach the later one?','A path may run through intermediate events even when there is no direct link.'],
      ['Locate','A reachability threshold','The manuscript identifies the threshold for a power-law gap kernel.']
    ],
    cases:[
      ['9fc58f1abf0d4f','Inspect the conditions question','Which properties of the dynamics are necessary or sufficient for formation?','The general question remains open. Reachability is one narrower question with a mathematical answer.'],
      ['2c77e9edd13955','Read the reachability result','The paper treats reachability between two fixed times in a specified random partial order.','Its threshold concerns the graph model. The physical origin and persistence of an organizing state require separate arguments.']
    ]
  }
};
