#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_194319084485298498) {
   out_194319084485298498[0] = delta_x[0] + nom_x[0];
   out_194319084485298498[1] = delta_x[1] + nom_x[1];
   out_194319084485298498[2] = delta_x[2] + nom_x[2];
   out_194319084485298498[3] = delta_x[3] + nom_x[3];
   out_194319084485298498[4] = delta_x[4] + nom_x[4];
   out_194319084485298498[5] = delta_x[5] + nom_x[5];
   out_194319084485298498[6] = delta_x[6] + nom_x[6];
   out_194319084485298498[7] = delta_x[7] + nom_x[7];
   out_194319084485298498[8] = delta_x[8] + nom_x[8];
   out_194319084485298498[9] = delta_x[9] + nom_x[9];
   out_194319084485298498[10] = delta_x[10] + nom_x[10];
   out_194319084485298498[11] = delta_x[11] + nom_x[11];
   out_194319084485298498[12] = delta_x[12] + nom_x[12];
   out_194319084485298498[13] = delta_x[13] + nom_x[13];
   out_194319084485298498[14] = delta_x[14] + nom_x[14];
   out_194319084485298498[15] = delta_x[15] + nom_x[15];
   out_194319084485298498[16] = delta_x[16] + nom_x[16];
   out_194319084485298498[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3875792020278493141) {
   out_3875792020278493141[0] = -nom_x[0] + true_x[0];
   out_3875792020278493141[1] = -nom_x[1] + true_x[1];
   out_3875792020278493141[2] = -nom_x[2] + true_x[2];
   out_3875792020278493141[3] = -nom_x[3] + true_x[3];
   out_3875792020278493141[4] = -nom_x[4] + true_x[4];
   out_3875792020278493141[5] = -nom_x[5] + true_x[5];
   out_3875792020278493141[6] = -nom_x[6] + true_x[6];
   out_3875792020278493141[7] = -nom_x[7] + true_x[7];
   out_3875792020278493141[8] = -nom_x[8] + true_x[8];
   out_3875792020278493141[9] = -nom_x[9] + true_x[9];
   out_3875792020278493141[10] = -nom_x[10] + true_x[10];
   out_3875792020278493141[11] = -nom_x[11] + true_x[11];
   out_3875792020278493141[12] = -nom_x[12] + true_x[12];
   out_3875792020278493141[13] = -nom_x[13] + true_x[13];
   out_3875792020278493141[14] = -nom_x[14] + true_x[14];
   out_3875792020278493141[15] = -nom_x[15] + true_x[15];
   out_3875792020278493141[16] = -nom_x[16] + true_x[16];
   out_3875792020278493141[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_1771566842897329361) {
   out_1771566842897329361[0] = 1.0;
   out_1771566842897329361[1] = 0.0;
   out_1771566842897329361[2] = 0.0;
   out_1771566842897329361[3] = 0.0;
   out_1771566842897329361[4] = 0.0;
   out_1771566842897329361[5] = 0.0;
   out_1771566842897329361[6] = 0.0;
   out_1771566842897329361[7] = 0.0;
   out_1771566842897329361[8] = 0.0;
   out_1771566842897329361[9] = 0.0;
   out_1771566842897329361[10] = 0.0;
   out_1771566842897329361[11] = 0.0;
   out_1771566842897329361[12] = 0.0;
   out_1771566842897329361[13] = 0.0;
   out_1771566842897329361[14] = 0.0;
   out_1771566842897329361[15] = 0.0;
   out_1771566842897329361[16] = 0.0;
   out_1771566842897329361[17] = 0.0;
   out_1771566842897329361[18] = 0.0;
   out_1771566842897329361[19] = 1.0;
   out_1771566842897329361[20] = 0.0;
   out_1771566842897329361[21] = 0.0;
   out_1771566842897329361[22] = 0.0;
   out_1771566842897329361[23] = 0.0;
   out_1771566842897329361[24] = 0.0;
   out_1771566842897329361[25] = 0.0;
   out_1771566842897329361[26] = 0.0;
   out_1771566842897329361[27] = 0.0;
   out_1771566842897329361[28] = 0.0;
   out_1771566842897329361[29] = 0.0;
   out_1771566842897329361[30] = 0.0;
   out_1771566842897329361[31] = 0.0;
   out_1771566842897329361[32] = 0.0;
   out_1771566842897329361[33] = 0.0;
   out_1771566842897329361[34] = 0.0;
   out_1771566842897329361[35] = 0.0;
   out_1771566842897329361[36] = 0.0;
   out_1771566842897329361[37] = 0.0;
   out_1771566842897329361[38] = 1.0;
   out_1771566842897329361[39] = 0.0;
   out_1771566842897329361[40] = 0.0;
   out_1771566842897329361[41] = 0.0;
   out_1771566842897329361[42] = 0.0;
   out_1771566842897329361[43] = 0.0;
   out_1771566842897329361[44] = 0.0;
   out_1771566842897329361[45] = 0.0;
   out_1771566842897329361[46] = 0.0;
   out_1771566842897329361[47] = 0.0;
   out_1771566842897329361[48] = 0.0;
   out_1771566842897329361[49] = 0.0;
   out_1771566842897329361[50] = 0.0;
   out_1771566842897329361[51] = 0.0;
   out_1771566842897329361[52] = 0.0;
   out_1771566842897329361[53] = 0.0;
   out_1771566842897329361[54] = 0.0;
   out_1771566842897329361[55] = 0.0;
   out_1771566842897329361[56] = 0.0;
   out_1771566842897329361[57] = 1.0;
   out_1771566842897329361[58] = 0.0;
   out_1771566842897329361[59] = 0.0;
   out_1771566842897329361[60] = 0.0;
   out_1771566842897329361[61] = 0.0;
   out_1771566842897329361[62] = 0.0;
   out_1771566842897329361[63] = 0.0;
   out_1771566842897329361[64] = 0.0;
   out_1771566842897329361[65] = 0.0;
   out_1771566842897329361[66] = 0.0;
   out_1771566842897329361[67] = 0.0;
   out_1771566842897329361[68] = 0.0;
   out_1771566842897329361[69] = 0.0;
   out_1771566842897329361[70] = 0.0;
   out_1771566842897329361[71] = 0.0;
   out_1771566842897329361[72] = 0.0;
   out_1771566842897329361[73] = 0.0;
   out_1771566842897329361[74] = 0.0;
   out_1771566842897329361[75] = 0.0;
   out_1771566842897329361[76] = 1.0;
   out_1771566842897329361[77] = 0.0;
   out_1771566842897329361[78] = 0.0;
   out_1771566842897329361[79] = 0.0;
   out_1771566842897329361[80] = 0.0;
   out_1771566842897329361[81] = 0.0;
   out_1771566842897329361[82] = 0.0;
   out_1771566842897329361[83] = 0.0;
   out_1771566842897329361[84] = 0.0;
   out_1771566842897329361[85] = 0.0;
   out_1771566842897329361[86] = 0.0;
   out_1771566842897329361[87] = 0.0;
   out_1771566842897329361[88] = 0.0;
   out_1771566842897329361[89] = 0.0;
   out_1771566842897329361[90] = 0.0;
   out_1771566842897329361[91] = 0.0;
   out_1771566842897329361[92] = 0.0;
   out_1771566842897329361[93] = 0.0;
   out_1771566842897329361[94] = 0.0;
   out_1771566842897329361[95] = 1.0;
   out_1771566842897329361[96] = 0.0;
   out_1771566842897329361[97] = 0.0;
   out_1771566842897329361[98] = 0.0;
   out_1771566842897329361[99] = 0.0;
   out_1771566842897329361[100] = 0.0;
   out_1771566842897329361[101] = 0.0;
   out_1771566842897329361[102] = 0.0;
   out_1771566842897329361[103] = 0.0;
   out_1771566842897329361[104] = 0.0;
   out_1771566842897329361[105] = 0.0;
   out_1771566842897329361[106] = 0.0;
   out_1771566842897329361[107] = 0.0;
   out_1771566842897329361[108] = 0.0;
   out_1771566842897329361[109] = 0.0;
   out_1771566842897329361[110] = 0.0;
   out_1771566842897329361[111] = 0.0;
   out_1771566842897329361[112] = 0.0;
   out_1771566842897329361[113] = 0.0;
   out_1771566842897329361[114] = 1.0;
   out_1771566842897329361[115] = 0.0;
   out_1771566842897329361[116] = 0.0;
   out_1771566842897329361[117] = 0.0;
   out_1771566842897329361[118] = 0.0;
   out_1771566842897329361[119] = 0.0;
   out_1771566842897329361[120] = 0.0;
   out_1771566842897329361[121] = 0.0;
   out_1771566842897329361[122] = 0.0;
   out_1771566842897329361[123] = 0.0;
   out_1771566842897329361[124] = 0.0;
   out_1771566842897329361[125] = 0.0;
   out_1771566842897329361[126] = 0.0;
   out_1771566842897329361[127] = 0.0;
   out_1771566842897329361[128] = 0.0;
   out_1771566842897329361[129] = 0.0;
   out_1771566842897329361[130] = 0.0;
   out_1771566842897329361[131] = 0.0;
   out_1771566842897329361[132] = 0.0;
   out_1771566842897329361[133] = 1.0;
   out_1771566842897329361[134] = 0.0;
   out_1771566842897329361[135] = 0.0;
   out_1771566842897329361[136] = 0.0;
   out_1771566842897329361[137] = 0.0;
   out_1771566842897329361[138] = 0.0;
   out_1771566842897329361[139] = 0.0;
   out_1771566842897329361[140] = 0.0;
   out_1771566842897329361[141] = 0.0;
   out_1771566842897329361[142] = 0.0;
   out_1771566842897329361[143] = 0.0;
   out_1771566842897329361[144] = 0.0;
   out_1771566842897329361[145] = 0.0;
   out_1771566842897329361[146] = 0.0;
   out_1771566842897329361[147] = 0.0;
   out_1771566842897329361[148] = 0.0;
   out_1771566842897329361[149] = 0.0;
   out_1771566842897329361[150] = 0.0;
   out_1771566842897329361[151] = 0.0;
   out_1771566842897329361[152] = 1.0;
   out_1771566842897329361[153] = 0.0;
   out_1771566842897329361[154] = 0.0;
   out_1771566842897329361[155] = 0.0;
   out_1771566842897329361[156] = 0.0;
   out_1771566842897329361[157] = 0.0;
   out_1771566842897329361[158] = 0.0;
   out_1771566842897329361[159] = 0.0;
   out_1771566842897329361[160] = 0.0;
   out_1771566842897329361[161] = 0.0;
   out_1771566842897329361[162] = 0.0;
   out_1771566842897329361[163] = 0.0;
   out_1771566842897329361[164] = 0.0;
   out_1771566842897329361[165] = 0.0;
   out_1771566842897329361[166] = 0.0;
   out_1771566842897329361[167] = 0.0;
   out_1771566842897329361[168] = 0.0;
   out_1771566842897329361[169] = 0.0;
   out_1771566842897329361[170] = 0.0;
   out_1771566842897329361[171] = 1.0;
   out_1771566842897329361[172] = 0.0;
   out_1771566842897329361[173] = 0.0;
   out_1771566842897329361[174] = 0.0;
   out_1771566842897329361[175] = 0.0;
   out_1771566842897329361[176] = 0.0;
   out_1771566842897329361[177] = 0.0;
   out_1771566842897329361[178] = 0.0;
   out_1771566842897329361[179] = 0.0;
   out_1771566842897329361[180] = 0.0;
   out_1771566842897329361[181] = 0.0;
   out_1771566842897329361[182] = 0.0;
   out_1771566842897329361[183] = 0.0;
   out_1771566842897329361[184] = 0.0;
   out_1771566842897329361[185] = 0.0;
   out_1771566842897329361[186] = 0.0;
   out_1771566842897329361[187] = 0.0;
   out_1771566842897329361[188] = 0.0;
   out_1771566842897329361[189] = 0.0;
   out_1771566842897329361[190] = 1.0;
   out_1771566842897329361[191] = 0.0;
   out_1771566842897329361[192] = 0.0;
   out_1771566842897329361[193] = 0.0;
   out_1771566842897329361[194] = 0.0;
   out_1771566842897329361[195] = 0.0;
   out_1771566842897329361[196] = 0.0;
   out_1771566842897329361[197] = 0.0;
   out_1771566842897329361[198] = 0.0;
   out_1771566842897329361[199] = 0.0;
   out_1771566842897329361[200] = 0.0;
   out_1771566842897329361[201] = 0.0;
   out_1771566842897329361[202] = 0.0;
   out_1771566842897329361[203] = 0.0;
   out_1771566842897329361[204] = 0.0;
   out_1771566842897329361[205] = 0.0;
   out_1771566842897329361[206] = 0.0;
   out_1771566842897329361[207] = 0.0;
   out_1771566842897329361[208] = 0.0;
   out_1771566842897329361[209] = 1.0;
   out_1771566842897329361[210] = 0.0;
   out_1771566842897329361[211] = 0.0;
   out_1771566842897329361[212] = 0.0;
   out_1771566842897329361[213] = 0.0;
   out_1771566842897329361[214] = 0.0;
   out_1771566842897329361[215] = 0.0;
   out_1771566842897329361[216] = 0.0;
   out_1771566842897329361[217] = 0.0;
   out_1771566842897329361[218] = 0.0;
   out_1771566842897329361[219] = 0.0;
   out_1771566842897329361[220] = 0.0;
   out_1771566842897329361[221] = 0.0;
   out_1771566842897329361[222] = 0.0;
   out_1771566842897329361[223] = 0.0;
   out_1771566842897329361[224] = 0.0;
   out_1771566842897329361[225] = 0.0;
   out_1771566842897329361[226] = 0.0;
   out_1771566842897329361[227] = 0.0;
   out_1771566842897329361[228] = 1.0;
   out_1771566842897329361[229] = 0.0;
   out_1771566842897329361[230] = 0.0;
   out_1771566842897329361[231] = 0.0;
   out_1771566842897329361[232] = 0.0;
   out_1771566842897329361[233] = 0.0;
   out_1771566842897329361[234] = 0.0;
   out_1771566842897329361[235] = 0.0;
   out_1771566842897329361[236] = 0.0;
   out_1771566842897329361[237] = 0.0;
   out_1771566842897329361[238] = 0.0;
   out_1771566842897329361[239] = 0.0;
   out_1771566842897329361[240] = 0.0;
   out_1771566842897329361[241] = 0.0;
   out_1771566842897329361[242] = 0.0;
   out_1771566842897329361[243] = 0.0;
   out_1771566842897329361[244] = 0.0;
   out_1771566842897329361[245] = 0.0;
   out_1771566842897329361[246] = 0.0;
   out_1771566842897329361[247] = 1.0;
   out_1771566842897329361[248] = 0.0;
   out_1771566842897329361[249] = 0.0;
   out_1771566842897329361[250] = 0.0;
   out_1771566842897329361[251] = 0.0;
   out_1771566842897329361[252] = 0.0;
   out_1771566842897329361[253] = 0.0;
   out_1771566842897329361[254] = 0.0;
   out_1771566842897329361[255] = 0.0;
   out_1771566842897329361[256] = 0.0;
   out_1771566842897329361[257] = 0.0;
   out_1771566842897329361[258] = 0.0;
   out_1771566842897329361[259] = 0.0;
   out_1771566842897329361[260] = 0.0;
   out_1771566842897329361[261] = 0.0;
   out_1771566842897329361[262] = 0.0;
   out_1771566842897329361[263] = 0.0;
   out_1771566842897329361[264] = 0.0;
   out_1771566842897329361[265] = 0.0;
   out_1771566842897329361[266] = 1.0;
   out_1771566842897329361[267] = 0.0;
   out_1771566842897329361[268] = 0.0;
   out_1771566842897329361[269] = 0.0;
   out_1771566842897329361[270] = 0.0;
   out_1771566842897329361[271] = 0.0;
   out_1771566842897329361[272] = 0.0;
   out_1771566842897329361[273] = 0.0;
   out_1771566842897329361[274] = 0.0;
   out_1771566842897329361[275] = 0.0;
   out_1771566842897329361[276] = 0.0;
   out_1771566842897329361[277] = 0.0;
   out_1771566842897329361[278] = 0.0;
   out_1771566842897329361[279] = 0.0;
   out_1771566842897329361[280] = 0.0;
   out_1771566842897329361[281] = 0.0;
   out_1771566842897329361[282] = 0.0;
   out_1771566842897329361[283] = 0.0;
   out_1771566842897329361[284] = 0.0;
   out_1771566842897329361[285] = 1.0;
   out_1771566842897329361[286] = 0.0;
   out_1771566842897329361[287] = 0.0;
   out_1771566842897329361[288] = 0.0;
   out_1771566842897329361[289] = 0.0;
   out_1771566842897329361[290] = 0.0;
   out_1771566842897329361[291] = 0.0;
   out_1771566842897329361[292] = 0.0;
   out_1771566842897329361[293] = 0.0;
   out_1771566842897329361[294] = 0.0;
   out_1771566842897329361[295] = 0.0;
   out_1771566842897329361[296] = 0.0;
   out_1771566842897329361[297] = 0.0;
   out_1771566842897329361[298] = 0.0;
   out_1771566842897329361[299] = 0.0;
   out_1771566842897329361[300] = 0.0;
   out_1771566842897329361[301] = 0.0;
   out_1771566842897329361[302] = 0.0;
   out_1771566842897329361[303] = 0.0;
   out_1771566842897329361[304] = 1.0;
   out_1771566842897329361[305] = 0.0;
   out_1771566842897329361[306] = 0.0;
   out_1771566842897329361[307] = 0.0;
   out_1771566842897329361[308] = 0.0;
   out_1771566842897329361[309] = 0.0;
   out_1771566842897329361[310] = 0.0;
   out_1771566842897329361[311] = 0.0;
   out_1771566842897329361[312] = 0.0;
   out_1771566842897329361[313] = 0.0;
   out_1771566842897329361[314] = 0.0;
   out_1771566842897329361[315] = 0.0;
   out_1771566842897329361[316] = 0.0;
   out_1771566842897329361[317] = 0.0;
   out_1771566842897329361[318] = 0.0;
   out_1771566842897329361[319] = 0.0;
   out_1771566842897329361[320] = 0.0;
   out_1771566842897329361[321] = 0.0;
   out_1771566842897329361[322] = 0.0;
   out_1771566842897329361[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8146104394789039778) {
   out_8146104394789039778[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8146104394789039778[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8146104394789039778[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8146104394789039778[3] = dt*state[12] + state[3];
   out_8146104394789039778[4] = dt*state[13] + state[4];
   out_8146104394789039778[5] = dt*state[14] + state[5];
   out_8146104394789039778[6] = state[6];
   out_8146104394789039778[7] = state[7];
   out_8146104394789039778[8] = state[8];
   out_8146104394789039778[9] = state[9];
   out_8146104394789039778[10] = state[10];
   out_8146104394789039778[11] = state[11];
   out_8146104394789039778[12] = state[12];
   out_8146104394789039778[13] = state[13];
   out_8146104394789039778[14] = state[14];
   out_8146104394789039778[15] = state[15];
   out_8146104394789039778[16] = state[16];
   out_8146104394789039778[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4695693737521448956) {
   out_4695693737521448956[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695693737521448956[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695693737521448956[2] = 0;
   out_4695693737521448956[3] = 0;
   out_4695693737521448956[4] = 0;
   out_4695693737521448956[5] = 0;
   out_4695693737521448956[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695693737521448956[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695693737521448956[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4695693737521448956[9] = 0;
   out_4695693737521448956[10] = 0;
   out_4695693737521448956[11] = 0;
   out_4695693737521448956[12] = 0;
   out_4695693737521448956[13] = 0;
   out_4695693737521448956[14] = 0;
   out_4695693737521448956[15] = 0;
   out_4695693737521448956[16] = 0;
   out_4695693737521448956[17] = 0;
   out_4695693737521448956[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4695693737521448956[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4695693737521448956[20] = 0;
   out_4695693737521448956[21] = 0;
   out_4695693737521448956[22] = 0;
   out_4695693737521448956[23] = 0;
   out_4695693737521448956[24] = 0;
   out_4695693737521448956[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4695693737521448956[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4695693737521448956[27] = 0;
   out_4695693737521448956[28] = 0;
   out_4695693737521448956[29] = 0;
   out_4695693737521448956[30] = 0;
   out_4695693737521448956[31] = 0;
   out_4695693737521448956[32] = 0;
   out_4695693737521448956[33] = 0;
   out_4695693737521448956[34] = 0;
   out_4695693737521448956[35] = 0;
   out_4695693737521448956[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695693737521448956[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695693737521448956[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695693737521448956[39] = 0;
   out_4695693737521448956[40] = 0;
   out_4695693737521448956[41] = 0;
   out_4695693737521448956[42] = 0;
   out_4695693737521448956[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695693737521448956[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4695693737521448956[45] = 0;
   out_4695693737521448956[46] = 0;
   out_4695693737521448956[47] = 0;
   out_4695693737521448956[48] = 0;
   out_4695693737521448956[49] = 0;
   out_4695693737521448956[50] = 0;
   out_4695693737521448956[51] = 0;
   out_4695693737521448956[52] = 0;
   out_4695693737521448956[53] = 0;
   out_4695693737521448956[54] = 0;
   out_4695693737521448956[55] = 0;
   out_4695693737521448956[56] = 0;
   out_4695693737521448956[57] = 1;
   out_4695693737521448956[58] = 0;
   out_4695693737521448956[59] = 0;
   out_4695693737521448956[60] = 0;
   out_4695693737521448956[61] = 0;
   out_4695693737521448956[62] = 0;
   out_4695693737521448956[63] = 0;
   out_4695693737521448956[64] = 0;
   out_4695693737521448956[65] = 0;
   out_4695693737521448956[66] = dt;
   out_4695693737521448956[67] = 0;
   out_4695693737521448956[68] = 0;
   out_4695693737521448956[69] = 0;
   out_4695693737521448956[70] = 0;
   out_4695693737521448956[71] = 0;
   out_4695693737521448956[72] = 0;
   out_4695693737521448956[73] = 0;
   out_4695693737521448956[74] = 0;
   out_4695693737521448956[75] = 0;
   out_4695693737521448956[76] = 1;
   out_4695693737521448956[77] = 0;
   out_4695693737521448956[78] = 0;
   out_4695693737521448956[79] = 0;
   out_4695693737521448956[80] = 0;
   out_4695693737521448956[81] = 0;
   out_4695693737521448956[82] = 0;
   out_4695693737521448956[83] = 0;
   out_4695693737521448956[84] = 0;
   out_4695693737521448956[85] = dt;
   out_4695693737521448956[86] = 0;
   out_4695693737521448956[87] = 0;
   out_4695693737521448956[88] = 0;
   out_4695693737521448956[89] = 0;
   out_4695693737521448956[90] = 0;
   out_4695693737521448956[91] = 0;
   out_4695693737521448956[92] = 0;
   out_4695693737521448956[93] = 0;
   out_4695693737521448956[94] = 0;
   out_4695693737521448956[95] = 1;
   out_4695693737521448956[96] = 0;
   out_4695693737521448956[97] = 0;
   out_4695693737521448956[98] = 0;
   out_4695693737521448956[99] = 0;
   out_4695693737521448956[100] = 0;
   out_4695693737521448956[101] = 0;
   out_4695693737521448956[102] = 0;
   out_4695693737521448956[103] = 0;
   out_4695693737521448956[104] = dt;
   out_4695693737521448956[105] = 0;
   out_4695693737521448956[106] = 0;
   out_4695693737521448956[107] = 0;
   out_4695693737521448956[108] = 0;
   out_4695693737521448956[109] = 0;
   out_4695693737521448956[110] = 0;
   out_4695693737521448956[111] = 0;
   out_4695693737521448956[112] = 0;
   out_4695693737521448956[113] = 0;
   out_4695693737521448956[114] = 1;
   out_4695693737521448956[115] = 0;
   out_4695693737521448956[116] = 0;
   out_4695693737521448956[117] = 0;
   out_4695693737521448956[118] = 0;
   out_4695693737521448956[119] = 0;
   out_4695693737521448956[120] = 0;
   out_4695693737521448956[121] = 0;
   out_4695693737521448956[122] = 0;
   out_4695693737521448956[123] = 0;
   out_4695693737521448956[124] = 0;
   out_4695693737521448956[125] = 0;
   out_4695693737521448956[126] = 0;
   out_4695693737521448956[127] = 0;
   out_4695693737521448956[128] = 0;
   out_4695693737521448956[129] = 0;
   out_4695693737521448956[130] = 0;
   out_4695693737521448956[131] = 0;
   out_4695693737521448956[132] = 0;
   out_4695693737521448956[133] = 1;
   out_4695693737521448956[134] = 0;
   out_4695693737521448956[135] = 0;
   out_4695693737521448956[136] = 0;
   out_4695693737521448956[137] = 0;
   out_4695693737521448956[138] = 0;
   out_4695693737521448956[139] = 0;
   out_4695693737521448956[140] = 0;
   out_4695693737521448956[141] = 0;
   out_4695693737521448956[142] = 0;
   out_4695693737521448956[143] = 0;
   out_4695693737521448956[144] = 0;
   out_4695693737521448956[145] = 0;
   out_4695693737521448956[146] = 0;
   out_4695693737521448956[147] = 0;
   out_4695693737521448956[148] = 0;
   out_4695693737521448956[149] = 0;
   out_4695693737521448956[150] = 0;
   out_4695693737521448956[151] = 0;
   out_4695693737521448956[152] = 1;
   out_4695693737521448956[153] = 0;
   out_4695693737521448956[154] = 0;
   out_4695693737521448956[155] = 0;
   out_4695693737521448956[156] = 0;
   out_4695693737521448956[157] = 0;
   out_4695693737521448956[158] = 0;
   out_4695693737521448956[159] = 0;
   out_4695693737521448956[160] = 0;
   out_4695693737521448956[161] = 0;
   out_4695693737521448956[162] = 0;
   out_4695693737521448956[163] = 0;
   out_4695693737521448956[164] = 0;
   out_4695693737521448956[165] = 0;
   out_4695693737521448956[166] = 0;
   out_4695693737521448956[167] = 0;
   out_4695693737521448956[168] = 0;
   out_4695693737521448956[169] = 0;
   out_4695693737521448956[170] = 0;
   out_4695693737521448956[171] = 1;
   out_4695693737521448956[172] = 0;
   out_4695693737521448956[173] = 0;
   out_4695693737521448956[174] = 0;
   out_4695693737521448956[175] = 0;
   out_4695693737521448956[176] = 0;
   out_4695693737521448956[177] = 0;
   out_4695693737521448956[178] = 0;
   out_4695693737521448956[179] = 0;
   out_4695693737521448956[180] = 0;
   out_4695693737521448956[181] = 0;
   out_4695693737521448956[182] = 0;
   out_4695693737521448956[183] = 0;
   out_4695693737521448956[184] = 0;
   out_4695693737521448956[185] = 0;
   out_4695693737521448956[186] = 0;
   out_4695693737521448956[187] = 0;
   out_4695693737521448956[188] = 0;
   out_4695693737521448956[189] = 0;
   out_4695693737521448956[190] = 1;
   out_4695693737521448956[191] = 0;
   out_4695693737521448956[192] = 0;
   out_4695693737521448956[193] = 0;
   out_4695693737521448956[194] = 0;
   out_4695693737521448956[195] = 0;
   out_4695693737521448956[196] = 0;
   out_4695693737521448956[197] = 0;
   out_4695693737521448956[198] = 0;
   out_4695693737521448956[199] = 0;
   out_4695693737521448956[200] = 0;
   out_4695693737521448956[201] = 0;
   out_4695693737521448956[202] = 0;
   out_4695693737521448956[203] = 0;
   out_4695693737521448956[204] = 0;
   out_4695693737521448956[205] = 0;
   out_4695693737521448956[206] = 0;
   out_4695693737521448956[207] = 0;
   out_4695693737521448956[208] = 0;
   out_4695693737521448956[209] = 1;
   out_4695693737521448956[210] = 0;
   out_4695693737521448956[211] = 0;
   out_4695693737521448956[212] = 0;
   out_4695693737521448956[213] = 0;
   out_4695693737521448956[214] = 0;
   out_4695693737521448956[215] = 0;
   out_4695693737521448956[216] = 0;
   out_4695693737521448956[217] = 0;
   out_4695693737521448956[218] = 0;
   out_4695693737521448956[219] = 0;
   out_4695693737521448956[220] = 0;
   out_4695693737521448956[221] = 0;
   out_4695693737521448956[222] = 0;
   out_4695693737521448956[223] = 0;
   out_4695693737521448956[224] = 0;
   out_4695693737521448956[225] = 0;
   out_4695693737521448956[226] = 0;
   out_4695693737521448956[227] = 0;
   out_4695693737521448956[228] = 1;
   out_4695693737521448956[229] = 0;
   out_4695693737521448956[230] = 0;
   out_4695693737521448956[231] = 0;
   out_4695693737521448956[232] = 0;
   out_4695693737521448956[233] = 0;
   out_4695693737521448956[234] = 0;
   out_4695693737521448956[235] = 0;
   out_4695693737521448956[236] = 0;
   out_4695693737521448956[237] = 0;
   out_4695693737521448956[238] = 0;
   out_4695693737521448956[239] = 0;
   out_4695693737521448956[240] = 0;
   out_4695693737521448956[241] = 0;
   out_4695693737521448956[242] = 0;
   out_4695693737521448956[243] = 0;
   out_4695693737521448956[244] = 0;
   out_4695693737521448956[245] = 0;
   out_4695693737521448956[246] = 0;
   out_4695693737521448956[247] = 1;
   out_4695693737521448956[248] = 0;
   out_4695693737521448956[249] = 0;
   out_4695693737521448956[250] = 0;
   out_4695693737521448956[251] = 0;
   out_4695693737521448956[252] = 0;
   out_4695693737521448956[253] = 0;
   out_4695693737521448956[254] = 0;
   out_4695693737521448956[255] = 0;
   out_4695693737521448956[256] = 0;
   out_4695693737521448956[257] = 0;
   out_4695693737521448956[258] = 0;
   out_4695693737521448956[259] = 0;
   out_4695693737521448956[260] = 0;
   out_4695693737521448956[261] = 0;
   out_4695693737521448956[262] = 0;
   out_4695693737521448956[263] = 0;
   out_4695693737521448956[264] = 0;
   out_4695693737521448956[265] = 0;
   out_4695693737521448956[266] = 1;
   out_4695693737521448956[267] = 0;
   out_4695693737521448956[268] = 0;
   out_4695693737521448956[269] = 0;
   out_4695693737521448956[270] = 0;
   out_4695693737521448956[271] = 0;
   out_4695693737521448956[272] = 0;
   out_4695693737521448956[273] = 0;
   out_4695693737521448956[274] = 0;
   out_4695693737521448956[275] = 0;
   out_4695693737521448956[276] = 0;
   out_4695693737521448956[277] = 0;
   out_4695693737521448956[278] = 0;
   out_4695693737521448956[279] = 0;
   out_4695693737521448956[280] = 0;
   out_4695693737521448956[281] = 0;
   out_4695693737521448956[282] = 0;
   out_4695693737521448956[283] = 0;
   out_4695693737521448956[284] = 0;
   out_4695693737521448956[285] = 1;
   out_4695693737521448956[286] = 0;
   out_4695693737521448956[287] = 0;
   out_4695693737521448956[288] = 0;
   out_4695693737521448956[289] = 0;
   out_4695693737521448956[290] = 0;
   out_4695693737521448956[291] = 0;
   out_4695693737521448956[292] = 0;
   out_4695693737521448956[293] = 0;
   out_4695693737521448956[294] = 0;
   out_4695693737521448956[295] = 0;
   out_4695693737521448956[296] = 0;
   out_4695693737521448956[297] = 0;
   out_4695693737521448956[298] = 0;
   out_4695693737521448956[299] = 0;
   out_4695693737521448956[300] = 0;
   out_4695693737521448956[301] = 0;
   out_4695693737521448956[302] = 0;
   out_4695693737521448956[303] = 0;
   out_4695693737521448956[304] = 1;
   out_4695693737521448956[305] = 0;
   out_4695693737521448956[306] = 0;
   out_4695693737521448956[307] = 0;
   out_4695693737521448956[308] = 0;
   out_4695693737521448956[309] = 0;
   out_4695693737521448956[310] = 0;
   out_4695693737521448956[311] = 0;
   out_4695693737521448956[312] = 0;
   out_4695693737521448956[313] = 0;
   out_4695693737521448956[314] = 0;
   out_4695693737521448956[315] = 0;
   out_4695693737521448956[316] = 0;
   out_4695693737521448956[317] = 0;
   out_4695693737521448956[318] = 0;
   out_4695693737521448956[319] = 0;
   out_4695693737521448956[320] = 0;
   out_4695693737521448956[321] = 0;
   out_4695693737521448956[322] = 0;
   out_4695693737521448956[323] = 1;
}
void h_4(double *state, double *unused, double *out_9158766820290338548) {
   out_9158766820290338548[0] = state[6] + state[9];
   out_9158766820290338548[1] = state[7] + state[10];
   out_9158766820290338548[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3591265568803626222) {
   out_3591265568803626222[0] = 0;
   out_3591265568803626222[1] = 0;
   out_3591265568803626222[2] = 0;
   out_3591265568803626222[3] = 0;
   out_3591265568803626222[4] = 0;
   out_3591265568803626222[5] = 0;
   out_3591265568803626222[6] = 1;
   out_3591265568803626222[7] = 0;
   out_3591265568803626222[8] = 0;
   out_3591265568803626222[9] = 1;
   out_3591265568803626222[10] = 0;
   out_3591265568803626222[11] = 0;
   out_3591265568803626222[12] = 0;
   out_3591265568803626222[13] = 0;
   out_3591265568803626222[14] = 0;
   out_3591265568803626222[15] = 0;
   out_3591265568803626222[16] = 0;
   out_3591265568803626222[17] = 0;
   out_3591265568803626222[18] = 0;
   out_3591265568803626222[19] = 0;
   out_3591265568803626222[20] = 0;
   out_3591265568803626222[21] = 0;
   out_3591265568803626222[22] = 0;
   out_3591265568803626222[23] = 0;
   out_3591265568803626222[24] = 0;
   out_3591265568803626222[25] = 1;
   out_3591265568803626222[26] = 0;
   out_3591265568803626222[27] = 0;
   out_3591265568803626222[28] = 1;
   out_3591265568803626222[29] = 0;
   out_3591265568803626222[30] = 0;
   out_3591265568803626222[31] = 0;
   out_3591265568803626222[32] = 0;
   out_3591265568803626222[33] = 0;
   out_3591265568803626222[34] = 0;
   out_3591265568803626222[35] = 0;
   out_3591265568803626222[36] = 0;
   out_3591265568803626222[37] = 0;
   out_3591265568803626222[38] = 0;
   out_3591265568803626222[39] = 0;
   out_3591265568803626222[40] = 0;
   out_3591265568803626222[41] = 0;
   out_3591265568803626222[42] = 0;
   out_3591265568803626222[43] = 0;
   out_3591265568803626222[44] = 1;
   out_3591265568803626222[45] = 0;
   out_3591265568803626222[46] = 0;
   out_3591265568803626222[47] = 1;
   out_3591265568803626222[48] = 0;
   out_3591265568803626222[49] = 0;
   out_3591265568803626222[50] = 0;
   out_3591265568803626222[51] = 0;
   out_3591265568803626222[52] = 0;
   out_3591265568803626222[53] = 0;
}
void h_10(double *state, double *unused, double *out_3868412619574276212) {
   out_3868412619574276212[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_3868412619574276212[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_3868412619574276212[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5591231114578616664) {
   out_5591231114578616664[0] = 0;
   out_5591231114578616664[1] = 9.8100000000000005*cos(state[1]);
   out_5591231114578616664[2] = 0;
   out_5591231114578616664[3] = 0;
   out_5591231114578616664[4] = -state[8];
   out_5591231114578616664[5] = state[7];
   out_5591231114578616664[6] = 0;
   out_5591231114578616664[7] = state[5];
   out_5591231114578616664[8] = -state[4];
   out_5591231114578616664[9] = 0;
   out_5591231114578616664[10] = 0;
   out_5591231114578616664[11] = 0;
   out_5591231114578616664[12] = 1;
   out_5591231114578616664[13] = 0;
   out_5591231114578616664[14] = 0;
   out_5591231114578616664[15] = 1;
   out_5591231114578616664[16] = 0;
   out_5591231114578616664[17] = 0;
   out_5591231114578616664[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5591231114578616664[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5591231114578616664[20] = 0;
   out_5591231114578616664[21] = state[8];
   out_5591231114578616664[22] = 0;
   out_5591231114578616664[23] = -state[6];
   out_5591231114578616664[24] = -state[5];
   out_5591231114578616664[25] = 0;
   out_5591231114578616664[26] = state[3];
   out_5591231114578616664[27] = 0;
   out_5591231114578616664[28] = 0;
   out_5591231114578616664[29] = 0;
   out_5591231114578616664[30] = 0;
   out_5591231114578616664[31] = 1;
   out_5591231114578616664[32] = 0;
   out_5591231114578616664[33] = 0;
   out_5591231114578616664[34] = 1;
   out_5591231114578616664[35] = 0;
   out_5591231114578616664[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5591231114578616664[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5591231114578616664[38] = 0;
   out_5591231114578616664[39] = -state[7];
   out_5591231114578616664[40] = state[6];
   out_5591231114578616664[41] = 0;
   out_5591231114578616664[42] = state[4];
   out_5591231114578616664[43] = -state[3];
   out_5591231114578616664[44] = 0;
   out_5591231114578616664[45] = 0;
   out_5591231114578616664[46] = 0;
   out_5591231114578616664[47] = 0;
   out_5591231114578616664[48] = 0;
   out_5591231114578616664[49] = 0;
   out_5591231114578616664[50] = 1;
   out_5591231114578616664[51] = 0;
   out_5591231114578616664[52] = 0;
   out_5591231114578616664[53] = 1;
}
void h_13(double *state, double *unused, double *out_9068407461977864951) {
   out_9068407461977864951[0] = state[3];
   out_9068407461977864951[1] = state[4];
   out_9068407461977864951[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4019365639513074707) {
   out_4019365639513074707[0] = 0;
   out_4019365639513074707[1] = 0;
   out_4019365639513074707[2] = 0;
   out_4019365639513074707[3] = 1;
   out_4019365639513074707[4] = 0;
   out_4019365639513074707[5] = 0;
   out_4019365639513074707[6] = 0;
   out_4019365639513074707[7] = 0;
   out_4019365639513074707[8] = 0;
   out_4019365639513074707[9] = 0;
   out_4019365639513074707[10] = 0;
   out_4019365639513074707[11] = 0;
   out_4019365639513074707[12] = 0;
   out_4019365639513074707[13] = 0;
   out_4019365639513074707[14] = 0;
   out_4019365639513074707[15] = 0;
   out_4019365639513074707[16] = 0;
   out_4019365639513074707[17] = 0;
   out_4019365639513074707[18] = 0;
   out_4019365639513074707[19] = 0;
   out_4019365639513074707[20] = 0;
   out_4019365639513074707[21] = 0;
   out_4019365639513074707[22] = 1;
   out_4019365639513074707[23] = 0;
   out_4019365639513074707[24] = 0;
   out_4019365639513074707[25] = 0;
   out_4019365639513074707[26] = 0;
   out_4019365639513074707[27] = 0;
   out_4019365639513074707[28] = 0;
   out_4019365639513074707[29] = 0;
   out_4019365639513074707[30] = 0;
   out_4019365639513074707[31] = 0;
   out_4019365639513074707[32] = 0;
   out_4019365639513074707[33] = 0;
   out_4019365639513074707[34] = 0;
   out_4019365639513074707[35] = 0;
   out_4019365639513074707[36] = 0;
   out_4019365639513074707[37] = 0;
   out_4019365639513074707[38] = 0;
   out_4019365639513074707[39] = 0;
   out_4019365639513074707[40] = 0;
   out_4019365639513074707[41] = 1;
   out_4019365639513074707[42] = 0;
   out_4019365639513074707[43] = 0;
   out_4019365639513074707[44] = 0;
   out_4019365639513074707[45] = 0;
   out_4019365639513074707[46] = 0;
   out_4019365639513074707[47] = 0;
   out_4019365639513074707[48] = 0;
   out_4019365639513074707[49] = 0;
   out_4019365639513074707[50] = 0;
   out_4019365639513074707[51] = 0;
   out_4019365639513074707[52] = 0;
   out_4019365639513074707[53] = 0;
}
void h_14(double *state, double *unused, double *out_9078119357886002753) {
   out_9078119357886002753[0] = state[6];
   out_9078119357886002753[1] = state[7];
   out_9078119357886002753[2] = state[8];
}
void H_14(double *state, double *unused, double *out_371975287535858307) {
   out_371975287535858307[0] = 0;
   out_371975287535858307[1] = 0;
   out_371975287535858307[2] = 0;
   out_371975287535858307[3] = 0;
   out_371975287535858307[4] = 0;
   out_371975287535858307[5] = 0;
   out_371975287535858307[6] = 1;
   out_371975287535858307[7] = 0;
   out_371975287535858307[8] = 0;
   out_371975287535858307[9] = 0;
   out_371975287535858307[10] = 0;
   out_371975287535858307[11] = 0;
   out_371975287535858307[12] = 0;
   out_371975287535858307[13] = 0;
   out_371975287535858307[14] = 0;
   out_371975287535858307[15] = 0;
   out_371975287535858307[16] = 0;
   out_371975287535858307[17] = 0;
   out_371975287535858307[18] = 0;
   out_371975287535858307[19] = 0;
   out_371975287535858307[20] = 0;
   out_371975287535858307[21] = 0;
   out_371975287535858307[22] = 0;
   out_371975287535858307[23] = 0;
   out_371975287535858307[24] = 0;
   out_371975287535858307[25] = 1;
   out_371975287535858307[26] = 0;
   out_371975287535858307[27] = 0;
   out_371975287535858307[28] = 0;
   out_371975287535858307[29] = 0;
   out_371975287535858307[30] = 0;
   out_371975287535858307[31] = 0;
   out_371975287535858307[32] = 0;
   out_371975287535858307[33] = 0;
   out_371975287535858307[34] = 0;
   out_371975287535858307[35] = 0;
   out_371975287535858307[36] = 0;
   out_371975287535858307[37] = 0;
   out_371975287535858307[38] = 0;
   out_371975287535858307[39] = 0;
   out_371975287535858307[40] = 0;
   out_371975287535858307[41] = 0;
   out_371975287535858307[42] = 0;
   out_371975287535858307[43] = 0;
   out_371975287535858307[44] = 1;
   out_371975287535858307[45] = 0;
   out_371975287535858307[46] = 0;
   out_371975287535858307[47] = 0;
   out_371975287535858307[48] = 0;
   out_371975287535858307[49] = 0;
   out_371975287535858307[50] = 0;
   out_371975287535858307[51] = 0;
   out_371975287535858307[52] = 0;
   out_371975287535858307[53] = 0;
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

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_194319084485298498) {
  err_fun(nom_x, delta_x, out_194319084485298498);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3875792020278493141) {
  inv_err_fun(nom_x, true_x, out_3875792020278493141);
}
void pose_H_mod_fun(double *state, double *out_1771566842897329361) {
  H_mod_fun(state, out_1771566842897329361);
}
void pose_f_fun(double *state, double dt, double *out_8146104394789039778) {
  f_fun(state,  dt, out_8146104394789039778);
}
void pose_F_fun(double *state, double dt, double *out_4695693737521448956) {
  F_fun(state,  dt, out_4695693737521448956);
}
void pose_h_4(double *state, double *unused, double *out_9158766820290338548) {
  h_4(state, unused, out_9158766820290338548);
}
void pose_H_4(double *state, double *unused, double *out_3591265568803626222) {
  H_4(state, unused, out_3591265568803626222);
}
void pose_h_10(double *state, double *unused, double *out_3868412619574276212) {
  h_10(state, unused, out_3868412619574276212);
}
void pose_H_10(double *state, double *unused, double *out_5591231114578616664) {
  H_10(state, unused, out_5591231114578616664);
}
void pose_h_13(double *state, double *unused, double *out_9068407461977864951) {
  h_13(state, unused, out_9068407461977864951);
}
void pose_H_13(double *state, double *unused, double *out_4019365639513074707) {
  H_13(state, unused, out_4019365639513074707);
}
void pose_h_14(double *state, double *unused, double *out_9078119357886002753) {
  h_14(state, unused, out_9078119357886002753);
}
void pose_H_14(double *state, double *unused, double *out_371975287535858307) {
  H_14(state, unused, out_371975287535858307);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
