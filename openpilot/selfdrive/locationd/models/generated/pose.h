#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_2009436175951488598);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7332641761682687022);
void pose_H_mod_fun(double *state, double *out_4532021646888526941);
void pose_f_fun(double *state, double dt, double *out_8141779762803422453);
void pose_F_fun(double *state, double dt, double *out_307681165278517936);
void pose_h_4(double *state, double *unused, double *out_730619574876521421);
void pose_H_4(double *state, double *unused, double *out_4412340019169294401);
void pose_h_10(double *state, double *unused, double *out_3688636129409807966);
void pose_H_10(double *state, double *unused, double *out_888670171547737742);
void pose_h_13(double *state, double *unused, double *out_8334275717310075175);
void pose_H_13(double *state, double *unused, double *out_1200066193836961600);
void pose_h_14(double *state, double *unused, double *out_1312978299807738637);
void pose_H_14(double *state, double *unused, double *out_449099162829809872);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}