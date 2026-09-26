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
void car_err_fun(double *nom_x, double *delta_x, double *out_3133799046682886501);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6107976784800433753);
void car_H_mod_fun(double *state, double *out_7581715153931950147);
void car_f_fun(double *state, double dt, double *out_4775660847937870558);
void car_F_fun(double *state, double dt, double *out_8119880649267268962);
void car_h_25(double *state, double *unused, double *out_15721789218837933);
void car_H_25(double *state, double *unused, double *out_7342048269788109792);
void car_h_24(double *state, double *unused, double *out_7885472985512316133);
void car_H_24(double *state, double *unused, double *out_3784122670985786656);
void car_h_30(double *state, double *unused, double *out_172908457569967078);
void car_H_30(double *state, double *unused, double *out_7471387216931349862);
void car_h_26(double *state, double *unused, double *out_5174581725230812723);
void car_H_26(double *state, double *unused, double *out_7363192485047385600);
void car_h_27(double *state, double *unused, double *out_3052507840663170618);
void car_H_27(double *state, double *unused, double *out_8800593544977776843);
void car_h_29(double *state, double *unused, double *out_4828764810090878567);
void car_H_29(double *state, double *unused, double *out_6961155872616957678);
void car_h_28(double *state, double *unused, double *out_3996017693564833053);
void car_H_28(double *state, double *unused, double *out_2004831801038695236);
void car_h_31(double *state, double *unused, double *out_6603549715695133096);
void car_H_31(double *state, double *unused, double *out_7311402307911149364);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}