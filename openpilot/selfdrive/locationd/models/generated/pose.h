#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_194319084485298498);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3875792020278493141);
void pose_H_mod_fun(double *state, double *out_1771566842897329361);
void pose_f_fun(double *state, double dt, double *out_8146104394789039778);
void pose_F_fun(double *state, double dt, double *out_4695693737521448956);
void pose_h_4(double *state, double *unused, double *out_9158766820290338548);
void pose_H_4(double *state, double *unused, double *out_3591265568803626222);
void pose_h_10(double *state, double *unused, double *out_3868412619574276212);
void pose_H_10(double *state, double *unused, double *out_5591231114578616664);
void pose_h_13(double *state, double *unused, double *out_9068407461977864951);
void pose_H_13(double *state, double *unused, double *out_4019365639513074707);
void pose_h_14(double *state, double *unused, double *out_9078119357886002753);
void pose_H_14(double *state, double *unused, double *out_371975287535858307);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}