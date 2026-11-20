import {routes as sfp} from '../physical-learning/atlas/map/routes.js';
import {routes as fold} from '../fold/atlas/map/routes.js';

export const programs = {
  sfp: {routes:sfp, initial:'cost', landmark:'Branch result'},
  fold: {routes:fold, initial:'existence', landmark:'Branch question'}
};
