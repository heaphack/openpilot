#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_5919091997198403016);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_2558825367884789217);
void car_H_mod_fun(double *state, double *out_6021957901702094314);
void car_f_fun(double *state, double dt, double *out_7916923738468198689);
void car_F_fun(double *state, double dt, double *out_6845694807970446584);
void car_h_25(double *state, double *unused, double *out_8093345101138084887);
void car_H_25(double *state, double *unused, double *out_6527292343902391026);
void car_h_24(double *state, double *unused, double *out_4588467170315459982);
void car_H_24(double *state, double *unused, double *out_6056834861859052302);
void car_h_30(double *state, double *unused, double *out_8650450772015309591);
void car_H_30(double *state, double *unused, double *out_6397953396759150956);
void car_h_26(double *state, double *unused, double *out_6046045451206611940);
void car_H_26(double *state, double *unused, double *out_2785789025028334802);
void car_h_27(double *state, double *unused, double *out_2549519538775791094);
void car_H_27(double *state, double *unused, double *out_4223190084958726045);
void car_h_29(double *state, double *unused, double *out_5331753111978258091);
void car_H_29(double *state, double *unused, double *out_6908184741073543140);
void car_h_28(double *state, double *unused, double *out_8532443378081932847);
void car_H_28(double *state, double *unused, double *out_8871815012638869391);
void car_h_31(double *state, double *unused, double *out_212072450384035702);
void car_H_31(double *state, double *unused, double *out_6557938305779351454);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}