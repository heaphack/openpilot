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
void err_fun(double *nom_x, double *delta_x, double *out_5919091997198403016) {
   out_5919091997198403016[0] = delta_x[0] + nom_x[0];
   out_5919091997198403016[1] = delta_x[1] + nom_x[1];
   out_5919091997198403016[2] = delta_x[2] + nom_x[2];
   out_5919091997198403016[3] = delta_x[3] + nom_x[3];
   out_5919091997198403016[4] = delta_x[4] + nom_x[4];
   out_5919091997198403016[5] = delta_x[5] + nom_x[5];
   out_5919091997198403016[6] = delta_x[6] + nom_x[6];
   out_5919091997198403016[7] = delta_x[7] + nom_x[7];
   out_5919091997198403016[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2558825367884789217) {
   out_2558825367884789217[0] = -nom_x[0] + true_x[0];
   out_2558825367884789217[1] = -nom_x[1] + true_x[1];
   out_2558825367884789217[2] = -nom_x[2] + true_x[2];
   out_2558825367884789217[3] = -nom_x[3] + true_x[3];
   out_2558825367884789217[4] = -nom_x[4] + true_x[4];
   out_2558825367884789217[5] = -nom_x[5] + true_x[5];
   out_2558825367884789217[6] = -nom_x[6] + true_x[6];
   out_2558825367884789217[7] = -nom_x[7] + true_x[7];
   out_2558825367884789217[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6021957901702094314) {
   out_6021957901702094314[0] = 1.0;
   out_6021957901702094314[1] = 0.0;
   out_6021957901702094314[2] = 0.0;
   out_6021957901702094314[3] = 0.0;
   out_6021957901702094314[4] = 0.0;
   out_6021957901702094314[5] = 0.0;
   out_6021957901702094314[6] = 0.0;
   out_6021957901702094314[7] = 0.0;
   out_6021957901702094314[8] = 0.0;
   out_6021957901702094314[9] = 0.0;
   out_6021957901702094314[10] = 1.0;
   out_6021957901702094314[11] = 0.0;
   out_6021957901702094314[12] = 0.0;
   out_6021957901702094314[13] = 0.0;
   out_6021957901702094314[14] = 0.0;
   out_6021957901702094314[15] = 0.0;
   out_6021957901702094314[16] = 0.0;
   out_6021957901702094314[17] = 0.0;
   out_6021957901702094314[18] = 0.0;
   out_6021957901702094314[19] = 0.0;
   out_6021957901702094314[20] = 1.0;
   out_6021957901702094314[21] = 0.0;
   out_6021957901702094314[22] = 0.0;
   out_6021957901702094314[23] = 0.0;
   out_6021957901702094314[24] = 0.0;
   out_6021957901702094314[25] = 0.0;
   out_6021957901702094314[26] = 0.0;
   out_6021957901702094314[27] = 0.0;
   out_6021957901702094314[28] = 0.0;
   out_6021957901702094314[29] = 0.0;
   out_6021957901702094314[30] = 1.0;
   out_6021957901702094314[31] = 0.0;
   out_6021957901702094314[32] = 0.0;
   out_6021957901702094314[33] = 0.0;
   out_6021957901702094314[34] = 0.0;
   out_6021957901702094314[35] = 0.0;
   out_6021957901702094314[36] = 0.0;
   out_6021957901702094314[37] = 0.0;
   out_6021957901702094314[38] = 0.0;
   out_6021957901702094314[39] = 0.0;
   out_6021957901702094314[40] = 1.0;
   out_6021957901702094314[41] = 0.0;
   out_6021957901702094314[42] = 0.0;
   out_6021957901702094314[43] = 0.0;
   out_6021957901702094314[44] = 0.0;
   out_6021957901702094314[45] = 0.0;
   out_6021957901702094314[46] = 0.0;
   out_6021957901702094314[47] = 0.0;
   out_6021957901702094314[48] = 0.0;
   out_6021957901702094314[49] = 0.0;
   out_6021957901702094314[50] = 1.0;
   out_6021957901702094314[51] = 0.0;
   out_6021957901702094314[52] = 0.0;
   out_6021957901702094314[53] = 0.0;
   out_6021957901702094314[54] = 0.0;
   out_6021957901702094314[55] = 0.0;
   out_6021957901702094314[56] = 0.0;
   out_6021957901702094314[57] = 0.0;
   out_6021957901702094314[58] = 0.0;
   out_6021957901702094314[59] = 0.0;
   out_6021957901702094314[60] = 1.0;
   out_6021957901702094314[61] = 0.0;
   out_6021957901702094314[62] = 0.0;
   out_6021957901702094314[63] = 0.0;
   out_6021957901702094314[64] = 0.0;
   out_6021957901702094314[65] = 0.0;
   out_6021957901702094314[66] = 0.0;
   out_6021957901702094314[67] = 0.0;
   out_6021957901702094314[68] = 0.0;
   out_6021957901702094314[69] = 0.0;
   out_6021957901702094314[70] = 1.0;
   out_6021957901702094314[71] = 0.0;
   out_6021957901702094314[72] = 0.0;
   out_6021957901702094314[73] = 0.0;
   out_6021957901702094314[74] = 0.0;
   out_6021957901702094314[75] = 0.0;
   out_6021957901702094314[76] = 0.0;
   out_6021957901702094314[77] = 0.0;
   out_6021957901702094314[78] = 0.0;
   out_6021957901702094314[79] = 0.0;
   out_6021957901702094314[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_7916923738468198689) {
   out_7916923738468198689[0] = state[0];
   out_7916923738468198689[1] = state[1];
   out_7916923738468198689[2] = state[2];
   out_7916923738468198689[3] = state[3];
   out_7916923738468198689[4] = state[4];
   out_7916923738468198689[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_7916923738468198689[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_7916923738468198689[7] = state[7];
   out_7916923738468198689[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6845694807970446584) {
   out_6845694807970446584[0] = 1;
   out_6845694807970446584[1] = 0;
   out_6845694807970446584[2] = 0;
   out_6845694807970446584[3] = 0;
   out_6845694807970446584[4] = 0;
   out_6845694807970446584[5] = 0;
   out_6845694807970446584[6] = 0;
   out_6845694807970446584[7] = 0;
   out_6845694807970446584[8] = 0;
   out_6845694807970446584[9] = 0;
   out_6845694807970446584[10] = 1;
   out_6845694807970446584[11] = 0;
   out_6845694807970446584[12] = 0;
   out_6845694807970446584[13] = 0;
   out_6845694807970446584[14] = 0;
   out_6845694807970446584[15] = 0;
   out_6845694807970446584[16] = 0;
   out_6845694807970446584[17] = 0;
   out_6845694807970446584[18] = 0;
   out_6845694807970446584[19] = 0;
   out_6845694807970446584[20] = 1;
   out_6845694807970446584[21] = 0;
   out_6845694807970446584[22] = 0;
   out_6845694807970446584[23] = 0;
   out_6845694807970446584[24] = 0;
   out_6845694807970446584[25] = 0;
   out_6845694807970446584[26] = 0;
   out_6845694807970446584[27] = 0;
   out_6845694807970446584[28] = 0;
   out_6845694807970446584[29] = 0;
   out_6845694807970446584[30] = 1;
   out_6845694807970446584[31] = 0;
   out_6845694807970446584[32] = 0;
   out_6845694807970446584[33] = 0;
   out_6845694807970446584[34] = 0;
   out_6845694807970446584[35] = 0;
   out_6845694807970446584[36] = 0;
   out_6845694807970446584[37] = 0;
   out_6845694807970446584[38] = 0;
   out_6845694807970446584[39] = 0;
   out_6845694807970446584[40] = 1;
   out_6845694807970446584[41] = 0;
   out_6845694807970446584[42] = 0;
   out_6845694807970446584[43] = 0;
   out_6845694807970446584[44] = 0;
   out_6845694807970446584[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6845694807970446584[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6845694807970446584[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6845694807970446584[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6845694807970446584[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6845694807970446584[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6845694807970446584[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6845694807970446584[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6845694807970446584[53] = -9.8100000000000005*dt;
   out_6845694807970446584[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6845694807970446584[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6845694807970446584[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6845694807970446584[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6845694807970446584[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6845694807970446584[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6845694807970446584[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6845694807970446584[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6845694807970446584[62] = 0;
   out_6845694807970446584[63] = 0;
   out_6845694807970446584[64] = 0;
   out_6845694807970446584[65] = 0;
   out_6845694807970446584[66] = 0;
   out_6845694807970446584[67] = 0;
   out_6845694807970446584[68] = 0;
   out_6845694807970446584[69] = 0;
   out_6845694807970446584[70] = 1;
   out_6845694807970446584[71] = 0;
   out_6845694807970446584[72] = 0;
   out_6845694807970446584[73] = 0;
   out_6845694807970446584[74] = 0;
   out_6845694807970446584[75] = 0;
   out_6845694807970446584[76] = 0;
   out_6845694807970446584[77] = 0;
   out_6845694807970446584[78] = 0;
   out_6845694807970446584[79] = 0;
   out_6845694807970446584[80] = 1;
}
void h_25(double *state, double *unused, double *out_8093345101138084887) {
   out_8093345101138084887[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6527292343902391026) {
   out_6527292343902391026[0] = 0;
   out_6527292343902391026[1] = 0;
   out_6527292343902391026[2] = 0;
   out_6527292343902391026[3] = 0;
   out_6527292343902391026[4] = 0;
   out_6527292343902391026[5] = 0;
   out_6527292343902391026[6] = 1;
   out_6527292343902391026[7] = 0;
   out_6527292343902391026[8] = 0;
}
void h_24(double *state, double *unused, double *out_4588467170315459982) {
   out_4588467170315459982[0] = state[4];
   out_4588467170315459982[1] = state[5];
}
void H_24(double *state, double *unused, double *out_6056834861859052302) {
   out_6056834861859052302[0] = 0;
   out_6056834861859052302[1] = 0;
   out_6056834861859052302[2] = 0;
   out_6056834861859052302[3] = 0;
   out_6056834861859052302[4] = 1;
   out_6056834861859052302[5] = 0;
   out_6056834861859052302[6] = 0;
   out_6056834861859052302[7] = 0;
   out_6056834861859052302[8] = 0;
   out_6056834861859052302[9] = 0;
   out_6056834861859052302[10] = 0;
   out_6056834861859052302[11] = 0;
   out_6056834861859052302[12] = 0;
   out_6056834861859052302[13] = 0;
   out_6056834861859052302[14] = 1;
   out_6056834861859052302[15] = 0;
   out_6056834861859052302[16] = 0;
   out_6056834861859052302[17] = 0;
}
void h_30(double *state, double *unused, double *out_8650450772015309591) {
   out_8650450772015309591[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6397953396759150956) {
   out_6397953396759150956[0] = 0;
   out_6397953396759150956[1] = 0;
   out_6397953396759150956[2] = 0;
   out_6397953396759150956[3] = 0;
   out_6397953396759150956[4] = 1;
   out_6397953396759150956[5] = 0;
   out_6397953396759150956[6] = 0;
   out_6397953396759150956[7] = 0;
   out_6397953396759150956[8] = 0;
}
void h_26(double *state, double *unused, double *out_6046045451206611940) {
   out_6046045451206611940[0] = state[7];
}
void H_26(double *state, double *unused, double *out_2785789025028334802) {
   out_2785789025028334802[0] = 0;
   out_2785789025028334802[1] = 0;
   out_2785789025028334802[2] = 0;
   out_2785789025028334802[3] = 0;
   out_2785789025028334802[4] = 0;
   out_2785789025028334802[5] = 0;
   out_2785789025028334802[6] = 0;
   out_2785789025028334802[7] = 1;
   out_2785789025028334802[8] = 0;
}
void h_27(double *state, double *unused, double *out_2549519538775791094) {
   out_2549519538775791094[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4223190084958726045) {
   out_4223190084958726045[0] = 0;
   out_4223190084958726045[1] = 0;
   out_4223190084958726045[2] = 0;
   out_4223190084958726045[3] = 1;
   out_4223190084958726045[4] = 0;
   out_4223190084958726045[5] = 0;
   out_4223190084958726045[6] = 0;
   out_4223190084958726045[7] = 0;
   out_4223190084958726045[8] = 0;
}
void h_29(double *state, double *unused, double *out_5331753111978258091) {
   out_5331753111978258091[0] = state[1];
}
void H_29(double *state, double *unused, double *out_6908184741073543140) {
   out_6908184741073543140[0] = 0;
   out_6908184741073543140[1] = 1;
   out_6908184741073543140[2] = 0;
   out_6908184741073543140[3] = 0;
   out_6908184741073543140[4] = 0;
   out_6908184741073543140[5] = 0;
   out_6908184741073543140[6] = 0;
   out_6908184741073543140[7] = 0;
   out_6908184741073543140[8] = 0;
}
void h_28(double *state, double *unused, double *out_8532443378081932847) {
   out_8532443378081932847[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8871815012638869391) {
   out_8871815012638869391[0] = 1;
   out_8871815012638869391[1] = 0;
   out_8871815012638869391[2] = 0;
   out_8871815012638869391[3] = 0;
   out_8871815012638869391[4] = 0;
   out_8871815012638869391[5] = 0;
   out_8871815012638869391[6] = 0;
   out_8871815012638869391[7] = 0;
   out_8871815012638869391[8] = 0;
}
void h_31(double *state, double *unused, double *out_212072450384035702) {
   out_212072450384035702[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6557938305779351454) {
   out_6557938305779351454[0] = 0;
   out_6557938305779351454[1] = 0;
   out_6557938305779351454[2] = 0;
   out_6557938305779351454[3] = 0;
   out_6557938305779351454[4] = 0;
   out_6557938305779351454[5] = 0;
   out_6557938305779351454[6] = 0;
   out_6557938305779351454[7] = 0;
   out_6557938305779351454[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_5919091997198403016) {
  err_fun(nom_x, delta_x, out_5919091997198403016);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2558825367884789217) {
  inv_err_fun(nom_x, true_x, out_2558825367884789217);
}
void car_H_mod_fun(double *state, double *out_6021957901702094314) {
  H_mod_fun(state, out_6021957901702094314);
}
void car_f_fun(double *state, double dt, double *out_7916923738468198689) {
  f_fun(state,  dt, out_7916923738468198689);
}
void car_F_fun(double *state, double dt, double *out_6845694807970446584) {
  F_fun(state,  dt, out_6845694807970446584);
}
void car_h_25(double *state, double *unused, double *out_8093345101138084887) {
  h_25(state, unused, out_8093345101138084887);
}
void car_H_25(double *state, double *unused, double *out_6527292343902391026) {
  H_25(state, unused, out_6527292343902391026);
}
void car_h_24(double *state, double *unused, double *out_4588467170315459982) {
  h_24(state, unused, out_4588467170315459982);
}
void car_H_24(double *state, double *unused, double *out_6056834861859052302) {
  H_24(state, unused, out_6056834861859052302);
}
void car_h_30(double *state, double *unused, double *out_8650450772015309591) {
  h_30(state, unused, out_8650450772015309591);
}
void car_H_30(double *state, double *unused, double *out_6397953396759150956) {
  H_30(state, unused, out_6397953396759150956);
}
void car_h_26(double *state, double *unused, double *out_6046045451206611940) {
  h_26(state, unused, out_6046045451206611940);
}
void car_H_26(double *state, double *unused, double *out_2785789025028334802) {
  H_26(state, unused, out_2785789025028334802);
}
void car_h_27(double *state, double *unused, double *out_2549519538775791094) {
  h_27(state, unused, out_2549519538775791094);
}
void car_H_27(double *state, double *unused, double *out_4223190084958726045) {
  H_27(state, unused, out_4223190084958726045);
}
void car_h_29(double *state, double *unused, double *out_5331753111978258091) {
  h_29(state, unused, out_5331753111978258091);
}
void car_H_29(double *state, double *unused, double *out_6908184741073543140) {
  H_29(state, unused, out_6908184741073543140);
}
void car_h_28(double *state, double *unused, double *out_8532443378081932847) {
  h_28(state, unused, out_8532443378081932847);
}
void car_H_28(double *state, double *unused, double *out_8871815012638869391) {
  H_28(state, unused, out_8871815012638869391);
}
void car_h_31(double *state, double *unused, double *out_212072450384035702) {
  h_31(state, unused, out_212072450384035702);
}
void car_H_31(double *state, double *unused, double *out_6557938305779351454) {
  H_31(state, unused, out_6557938305779351454);
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
