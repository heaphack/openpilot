#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_3133799046682886501) {
   out_3133799046682886501[0] = delta_x[0] + nom_x[0];
   out_3133799046682886501[1] = delta_x[1] + nom_x[1];
   out_3133799046682886501[2] = delta_x[2] + nom_x[2];
   out_3133799046682886501[3] = delta_x[3] + nom_x[3];
   out_3133799046682886501[4] = delta_x[4] + nom_x[4];
   out_3133799046682886501[5] = delta_x[5] + nom_x[5];
   out_3133799046682886501[6] = delta_x[6] + nom_x[6];
   out_3133799046682886501[7] = delta_x[7] + nom_x[7];
   out_3133799046682886501[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6107976784800433753) {
   out_6107976784800433753[0] = -nom_x[0] + true_x[0];
   out_6107976784800433753[1] = -nom_x[1] + true_x[1];
   out_6107976784800433753[2] = -nom_x[2] + true_x[2];
   out_6107976784800433753[3] = -nom_x[3] + true_x[3];
   out_6107976784800433753[4] = -nom_x[4] + true_x[4];
   out_6107976784800433753[5] = -nom_x[5] + true_x[5];
   out_6107976784800433753[6] = -nom_x[6] + true_x[6];
   out_6107976784800433753[7] = -nom_x[7] + true_x[7];
   out_6107976784800433753[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_7581715153931950147) {
   out_7581715153931950147[0] = 1.0;
   out_7581715153931950147[1] = 0.0;
   out_7581715153931950147[2] = 0.0;
   out_7581715153931950147[3] = 0.0;
   out_7581715153931950147[4] = 0.0;
   out_7581715153931950147[5] = 0.0;
   out_7581715153931950147[6] = 0.0;
   out_7581715153931950147[7] = 0.0;
   out_7581715153931950147[8] = 0.0;
   out_7581715153931950147[9] = 0.0;
   out_7581715153931950147[10] = 1.0;
   out_7581715153931950147[11] = 0.0;
   out_7581715153931950147[12] = 0.0;
   out_7581715153931950147[13] = 0.0;
   out_7581715153931950147[14] = 0.0;
   out_7581715153931950147[15] = 0.0;
   out_7581715153931950147[16] = 0.0;
   out_7581715153931950147[17] = 0.0;
   out_7581715153931950147[18] = 0.0;
   out_7581715153931950147[19] = 0.0;
   out_7581715153931950147[20] = 1.0;
   out_7581715153931950147[21] = 0.0;
   out_7581715153931950147[22] = 0.0;
   out_7581715153931950147[23] = 0.0;
   out_7581715153931950147[24] = 0.0;
   out_7581715153931950147[25] = 0.0;
   out_7581715153931950147[26] = 0.0;
   out_7581715153931950147[27] = 0.0;
   out_7581715153931950147[28] = 0.0;
   out_7581715153931950147[29] = 0.0;
   out_7581715153931950147[30] = 1.0;
   out_7581715153931950147[31] = 0.0;
   out_7581715153931950147[32] = 0.0;
   out_7581715153931950147[33] = 0.0;
   out_7581715153931950147[34] = 0.0;
   out_7581715153931950147[35] = 0.0;
   out_7581715153931950147[36] = 0.0;
   out_7581715153931950147[37] = 0.0;
   out_7581715153931950147[38] = 0.0;
   out_7581715153931950147[39] = 0.0;
   out_7581715153931950147[40] = 1.0;
   out_7581715153931950147[41] = 0.0;
   out_7581715153931950147[42] = 0.0;
   out_7581715153931950147[43] = 0.0;
   out_7581715153931950147[44] = 0.0;
   out_7581715153931950147[45] = 0.0;
   out_7581715153931950147[46] = 0.0;
   out_7581715153931950147[47] = 0.0;
   out_7581715153931950147[48] = 0.0;
   out_7581715153931950147[49] = 0.0;
   out_7581715153931950147[50] = 1.0;
   out_7581715153931950147[51] = 0.0;
   out_7581715153931950147[52] = 0.0;
   out_7581715153931950147[53] = 0.0;
   out_7581715153931950147[54] = 0.0;
   out_7581715153931950147[55] = 0.0;
   out_7581715153931950147[56] = 0.0;
   out_7581715153931950147[57] = 0.0;
   out_7581715153931950147[58] = 0.0;
   out_7581715153931950147[59] = 0.0;
   out_7581715153931950147[60] = 1.0;
   out_7581715153931950147[61] = 0.0;
   out_7581715153931950147[62] = 0.0;
   out_7581715153931950147[63] = 0.0;
   out_7581715153931950147[64] = 0.0;
   out_7581715153931950147[65] = 0.0;
   out_7581715153931950147[66] = 0.0;
   out_7581715153931950147[67] = 0.0;
   out_7581715153931950147[68] = 0.0;
   out_7581715153931950147[69] = 0.0;
   out_7581715153931950147[70] = 1.0;
   out_7581715153931950147[71] = 0.0;
   out_7581715153931950147[72] = 0.0;
   out_7581715153931950147[73] = 0.0;
   out_7581715153931950147[74] = 0.0;
   out_7581715153931950147[75] = 0.0;
   out_7581715153931950147[76] = 0.0;
   out_7581715153931950147[77] = 0.0;
   out_7581715153931950147[78] = 0.0;
   out_7581715153931950147[79] = 0.0;
   out_7581715153931950147[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4775660847937870558) {
   out_4775660847937870558[0] = state[0];
   out_4775660847937870558[1] = state[1];
   out_4775660847937870558[2] = state[2];
   out_4775660847937870558[3] = state[3];
   out_4775660847937870558[4] = state[4];
   out_4775660847937870558[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4775660847937870558[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4775660847937870558[7] = state[7];
   out_4775660847937870558[8] = state[8];
}
void F_fun(double *state, double dt, double *out_8119880649267268962) {
   out_8119880649267268962[0] = 1;
   out_8119880649267268962[1] = 0;
   out_8119880649267268962[2] = 0;
   out_8119880649267268962[3] = 0;
   out_8119880649267268962[4] = 0;
   out_8119880649267268962[5] = 0;
   out_8119880649267268962[6] = 0;
   out_8119880649267268962[7] = 0;
   out_8119880649267268962[8] = 0;
   out_8119880649267268962[9] = 0;
   out_8119880649267268962[10] = 1;
   out_8119880649267268962[11] = 0;
   out_8119880649267268962[12] = 0;
   out_8119880649267268962[13] = 0;
   out_8119880649267268962[14] = 0;
   out_8119880649267268962[15] = 0;
   out_8119880649267268962[16] = 0;
   out_8119880649267268962[17] = 0;
   out_8119880649267268962[18] = 0;
   out_8119880649267268962[19] = 0;
   out_8119880649267268962[20] = 1;
   out_8119880649267268962[21] = 0;
   out_8119880649267268962[22] = 0;
   out_8119880649267268962[23] = 0;
   out_8119880649267268962[24] = 0;
   out_8119880649267268962[25] = 0;
   out_8119880649267268962[26] = 0;
   out_8119880649267268962[27] = 0;
   out_8119880649267268962[28] = 0;
   out_8119880649267268962[29] = 0;
   out_8119880649267268962[30] = 1;
   out_8119880649267268962[31] = 0;
   out_8119880649267268962[32] = 0;
   out_8119880649267268962[33] = 0;
   out_8119880649267268962[34] = 0;
   out_8119880649267268962[35] = 0;
   out_8119880649267268962[36] = 0;
   out_8119880649267268962[37] = 0;
   out_8119880649267268962[38] = 0;
   out_8119880649267268962[39] = 0;
   out_8119880649267268962[40] = 1;
   out_8119880649267268962[41] = 0;
   out_8119880649267268962[42] = 0;
   out_8119880649267268962[43] = 0;
   out_8119880649267268962[44] = 0;
   out_8119880649267268962[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_8119880649267268962[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_8119880649267268962[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8119880649267268962[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8119880649267268962[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_8119880649267268962[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_8119880649267268962[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_8119880649267268962[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_8119880649267268962[53] = -9.8100000000000005*dt;
   out_8119880649267268962[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_8119880649267268962[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_8119880649267268962[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8119880649267268962[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8119880649267268962[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_8119880649267268962[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_8119880649267268962[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_8119880649267268962[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8119880649267268962[62] = 0;
   out_8119880649267268962[63] = 0;
   out_8119880649267268962[64] = 0;
   out_8119880649267268962[65] = 0;
   out_8119880649267268962[66] = 0;
   out_8119880649267268962[67] = 0;
   out_8119880649267268962[68] = 0;
   out_8119880649267268962[69] = 0;
   out_8119880649267268962[70] = 1;
   out_8119880649267268962[71] = 0;
   out_8119880649267268962[72] = 0;
   out_8119880649267268962[73] = 0;
   out_8119880649267268962[74] = 0;
   out_8119880649267268962[75] = 0;
   out_8119880649267268962[76] = 0;
   out_8119880649267268962[77] = 0;
   out_8119880649267268962[78] = 0;
   out_8119880649267268962[79] = 0;
   out_8119880649267268962[80] = 1;
}
void h_25(double *state, double *unused, double *out_15721789218837933) {
   out_15721789218837933[0] = state[6];
}
void H_25(double *state, double *unused, double *out_7342048269788109792) {
   out_7342048269788109792[0] = 0;
   out_7342048269788109792[1] = 0;
   out_7342048269788109792[2] = 0;
   out_7342048269788109792[3] = 0;
   out_7342048269788109792[4] = 0;
   out_7342048269788109792[5] = 0;
   out_7342048269788109792[6] = 1;
   out_7342048269788109792[7] = 0;
   out_7342048269788109792[8] = 0;
}
void h_24(double *state, double *unused, double *out_7885472985512316133) {
   out_7885472985512316133[0] = state[4];
   out_7885472985512316133[1] = state[5];
}
void H_24(double *state, double *unused, double *out_3784122670985786656) {
   out_3784122670985786656[0] = 0;
   out_3784122670985786656[1] = 0;
   out_3784122670985786656[2] = 0;
   out_3784122670985786656[3] = 0;
   out_3784122670985786656[4] = 1;
   out_3784122670985786656[5] = 0;
   out_3784122670985786656[6] = 0;
   out_3784122670985786656[7] = 0;
   out_3784122670985786656[8] = 0;
   out_3784122670985786656[9] = 0;
   out_3784122670985786656[10] = 0;
   out_3784122670985786656[11] = 0;
   out_3784122670985786656[12] = 0;
   out_3784122670985786656[13] = 0;
   out_3784122670985786656[14] = 1;
   out_3784122670985786656[15] = 0;
   out_3784122670985786656[16] = 0;
   out_3784122670985786656[17] = 0;
}
void h_30(double *state, double *unused, double *out_172908457569967078) {
   out_172908457569967078[0] = state[4];
}
void H_30(double *state, double *unused, double *out_7471387216931349862) {
   out_7471387216931349862[0] = 0;
   out_7471387216931349862[1] = 0;
   out_7471387216931349862[2] = 0;
   out_7471387216931349862[3] = 0;
   out_7471387216931349862[4] = 1;
   out_7471387216931349862[5] = 0;
   out_7471387216931349862[6] = 0;
   out_7471387216931349862[7] = 0;
   out_7471387216931349862[8] = 0;
}
void h_26(double *state, double *unused, double *out_5174581725230812723) {
   out_5174581725230812723[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7363192485047385600) {
   out_7363192485047385600[0] = 0;
   out_7363192485047385600[1] = 0;
   out_7363192485047385600[2] = 0;
   out_7363192485047385600[3] = 0;
   out_7363192485047385600[4] = 0;
   out_7363192485047385600[5] = 0;
   out_7363192485047385600[6] = 0;
   out_7363192485047385600[7] = 1;
   out_7363192485047385600[8] = 0;
}
void h_27(double *state, double *unused, double *out_3052507840663170618) {
   out_3052507840663170618[0] = state[3];
}
void H_27(double *state, double *unused, double *out_8800593544977776843) {
   out_8800593544977776843[0] = 0;
   out_8800593544977776843[1] = 0;
   out_8800593544977776843[2] = 0;
   out_8800593544977776843[3] = 1;
   out_8800593544977776843[4] = 0;
   out_8800593544977776843[5] = 0;
   out_8800593544977776843[6] = 0;
   out_8800593544977776843[7] = 0;
   out_8800593544977776843[8] = 0;
}
void h_29(double *state, double *unused, double *out_4828764810090878567) {
   out_4828764810090878567[0] = state[1];
}
void H_29(double *state, double *unused, double *out_6961155872616957678) {
   out_6961155872616957678[0] = 0;
   out_6961155872616957678[1] = 1;
   out_6961155872616957678[2] = 0;
   out_6961155872616957678[3] = 0;
   out_6961155872616957678[4] = 0;
   out_6961155872616957678[5] = 0;
   out_6961155872616957678[6] = 0;
   out_6961155872616957678[7] = 0;
   out_6961155872616957678[8] = 0;
}
void h_28(double *state, double *unused, double *out_3996017693564833053) {
   out_3996017693564833053[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2004831801038695236) {
   out_2004831801038695236[0] = 1;
   out_2004831801038695236[1] = 0;
   out_2004831801038695236[2] = 0;
   out_2004831801038695236[3] = 0;
   out_2004831801038695236[4] = 0;
   out_2004831801038695236[5] = 0;
   out_2004831801038695236[6] = 0;
   out_2004831801038695236[7] = 0;
   out_2004831801038695236[8] = 0;
}
void h_31(double *state, double *unused, double *out_6603549715695133096) {
   out_6603549715695133096[0] = state[8];
}
void H_31(double *state, double *unused, double *out_7311402307911149364) {
   out_7311402307911149364[0] = 0;
   out_7311402307911149364[1] = 0;
   out_7311402307911149364[2] = 0;
   out_7311402307911149364[3] = 0;
   out_7311402307911149364[4] = 0;
   out_7311402307911149364[5] = 0;
   out_7311402307911149364[6] = 0;
   out_7311402307911149364[7] = 0;
   out_7311402307911149364[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_3133799046682886501) {
  err_fun(nom_x, delta_x, out_3133799046682886501);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6107976784800433753) {
  inv_err_fun(nom_x, true_x, out_6107976784800433753);
}
void car_H_mod_fun(double *state, double *out_7581715153931950147) {
  H_mod_fun(state, out_7581715153931950147);
}
void car_f_fun(double *state, double dt, double *out_4775660847937870558) {
  f_fun(state,  dt, out_4775660847937870558);
}
void car_F_fun(double *state, double dt, double *out_8119880649267268962) {
  F_fun(state,  dt, out_8119880649267268962);
}
void car_h_25(double *state, double *unused, double *out_15721789218837933) {
  h_25(state, unused, out_15721789218837933);
}
void car_H_25(double *state, double *unused, double *out_7342048269788109792) {
  H_25(state, unused, out_7342048269788109792);
}
void car_h_24(double *state, double *unused, double *out_7885472985512316133) {
  h_24(state, unused, out_7885472985512316133);
}
void car_H_24(double *state, double *unused, double *out_3784122670985786656) {
  H_24(state, unused, out_3784122670985786656);
}
void car_h_30(double *state, double *unused, double *out_172908457569967078) {
  h_30(state, unused, out_172908457569967078);
}
void car_H_30(double *state, double *unused, double *out_7471387216931349862) {
  H_30(state, unused, out_7471387216931349862);
}
void car_h_26(double *state, double *unused, double *out_5174581725230812723) {
  h_26(state, unused, out_5174581725230812723);
}
void car_H_26(double *state, double *unused, double *out_7363192485047385600) {
  H_26(state, unused, out_7363192485047385600);
}
void car_h_27(double *state, double *unused, double *out_3052507840663170618) {
  h_27(state, unused, out_3052507840663170618);
}
void car_H_27(double *state, double *unused, double *out_8800593544977776843) {
  H_27(state, unused, out_8800593544977776843);
}
void car_h_29(double *state, double *unused, double *out_4828764810090878567) {
  h_29(state, unused, out_4828764810090878567);
}
void car_H_29(double *state, double *unused, double *out_6961155872616957678) {
  H_29(state, unused, out_6961155872616957678);
}
void car_h_28(double *state, double *unused, double *out_3996017693564833053) {
  h_28(state, unused, out_3996017693564833053);
}
void car_H_28(double *state, double *unused, double *out_2004831801038695236) {
  H_28(state, unused, out_2004831801038695236);
}
void car_h_31(double *state, double *unused, double *out_6603549715695133096) {
  h_31(state, unused, out_6603549715695133096);
}
void car_H_31(double *state, double *unused, double *out_7311402307911149364) {
  H_31(state, unused, out_7311402307911149364);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
