	.include "asm/macros.inc"

	.syntax unified
	
	.text

	thumb_func_start Actor8_Update
Actor8_Update: @ 0x080D1748
	push {r4, r5, r6, r7, lr}
	mov r7, sb
	mov r6, r8
	push {r6, r7}
	sub sp, #0x10
	adds r7, r0, #0
	ldrb r0, [r7, #0xd]
	cmp r0, #4
	bls _080D175C
	b _080D1CD8
_080D175C:
	lsls r0, r0, #2
	ldr r1, _080D1768 @ =_080D176C
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D1768: .4byte _080D176C
_080D176C: @ jump table
	.4byte _080D1780 @ case 0
	.4byte _080D1A60 @ case 1
	.4byte _080D1ADA @ case 2
	.4byte _080D1B8C @ case 3
	.4byte _080D1C1E @ case 4
_080D1780:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldrb r0, [r7, #0x11]
	cmp r0, #0
	bne _080D17CC
	ldrb r0, [r7, #0x12]
	subs r0, #1
	strb r0, [r7, #0x12]
	lsls r0, r0, #0x18
	lsrs r0, r0, #0x18
	cmp r0, #0xff
	bne _080D17CC
	ldr r2, _080D1908 @ =RNG_0202f388
	ldr r1, [r2]
	ldr r0, _080D190C @ =0x000343FD
	muls r0, r1, r0
	ldr r1, _080D1910 @ =0x00269EC3
	adds r0, r0, r1
	lsls r0, r0, #1
	lsrs r1, r0, #1
	str r1, [r2]
	lsrs r0, r0, #0x11
	movs r1, #0x7f
	ands r0, r1
	adds r0, #0x1e
	strb r0, [r7, #0x12]
	ldr r2, [r7, #0x54]
	ldr r3, _080D1914 @ =0xFFFFF000
	adds r2, r2, r3
	ldr r3, [r7, #0x68]
	movs r4, #0x80
	lsls r4, r4, #4
	adds r3, r3, r4
	movs r0, #1
	movs r1, #0
	bl FUN_080c5628
_080D17CC:
	ldr r0, [r7, #0x64]
	ldr r1, [r7, #0x68]
	bl FUN_080098a4
	lsls r0, r0, #0x10
	cmp r0, #0
	beq _080D17DC
	b _080D1CD8
_080D17DC:
	ldrb r0, [r7, #0xa]
	movs r1, #1
	orrs r1, r0
	strb r1, [r7, #0xa]
	ldrb r0, [r7, #0x11]
	cmp r0, #0
	beq _080D17EC
	b _080D1920
_080D17EC:
	adds r1, r7, #0
	adds r1, #0x54
	movs r0, #4
	bl AppendQuake
	ldr r4, _080D1918 @ =0x0000011D
	adds r0, r4, #0
	bl isSoundPlaying
	cmp r0, #0
	bne _080D1808
	adds r0, r4, #0
	bl PlaySound
_080D1808:
	ldr r0, [r7, #0x54]
	ldr r1, _080D1914 @ =0xFFFFF000
	mov sb, r1
	add r0, sb
	str r0, [sp, #8]
	ldr r0, [r7, #0x68]
	ldr r2, _080D191C @ =0xFFFFFE00
	adds r0, r0, r2
	str r0, [sp, #0xc]
	movs r0, #3
	add r1, sp, #8
	bl CreateSmoke
	ldr r0, [r7, #0x68]
	movs r4, #0x80
	lsls r4, r4, #4
	adds r0, r0, r4
	str r0, [sp, #0xc]
	movs r0, #3
	add r1, sp, #8
	bl CreateSmoke
	ldr r2, [r7, #0x54]
	add r2, sb
	ldr r3, [r7, #0x68]
	adds r3, r3, r4
	mov ip, r3
	ldr r3, _080D1908 @ =RNG_0202f388
	mov r8, r3
	ldr r0, [r3]
	ldr r6, _080D190C @ =0x000343FD
	muls r0, r6, r0
	ldr r4, _080D1910 @ =0x00269EC3
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	lsrs r0, r0, #0x11
	movs r5, #7
	ands r0, r5
	subs r0, #4
	lsls r0, r0, #7
	str r0, [sp]
	adds r0, r1, #0
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	str r1, [r3]
	lsrs r0, r0, #0x11
	ands r0, r5
	rsbs r0, r0, #0
	lsls r0, r0, #7
	str r0, [sp, #4]
	movs r0, #1
	movs r1, #3
	mov r3, ip
	bl FUN_080c5684
	ldr r2, [r7, #0x54]
	add r2, sb
	ldr r3, [r7, #0x68]
	movs r0, #0x80
	lsls r0, r0, #3
	adds r0, r0, r3
	mov ip, r0
	mov r1, r8
	ldr r0, [r1]
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	lsrs r0, r0, #0x11
	ands r0, r5
	subs r0, #4
	lsls r0, r0, #7
	str r0, [sp]
	adds r0, r1, #0
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	mov r3, r8
	str r1, [r3]
	lsrs r0, r0, #0x11
	ands r0, r5
	rsbs r0, r0, #0
	lsls r0, r0, #7
	str r0, [sp, #4]
	movs r0, #1
	movs r1, #5
	mov r3, ip
	bl FUN_080c5684
	ldr r2, [r7, #0x54]
	add r2, sb
	ldr r3, [r7, #0x68]
	mov r1, r8
	ldr r0, [r1]
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	lsrs r0, r0, #0x11
	ands r0, r5
	subs r0, #4
	lsls r0, r0, #7
	str r0, [sp]
	adds r0, r1, #0
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	mov r4, r8
	str r1, [r4]
	lsrs r0, r0, #0x11
	ands r0, r5
	rsbs r0, r0, #0
	lsls r0, r0, #7
	str r0, [sp, #4]
	movs r0, #1
	movs r1, #4
	bl FUN_080c5684
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
	b _080D1CD8
	.align 2, 0
_080D1908: .4byte RNG_0202f388
_080D190C: .4byte 0x000343FD
_080D1910: .4byte 0x00269EC3
_080D1914: .4byte 0xFFFFF000
_080D1918: .4byte 0x0000011D
_080D191C: .4byte 0xFFFFFE00
_080D1920:
	adds r1, r7, #0
	adds r1, #0x54
	movs r0, #0x10
	bl AppendQuake
	movs r0, #0x41
	bl PlaySound
	ldr r0, [r7, #0x54]
	ldr r1, _080D1A4C @ =0xFFFFF000
	adds r0, r0, r1
	str r0, [sp, #8]
	ldr r0, [r7, #0x58]
	str r0, [sp, #0xc]
	movs r0, #3
	add r1, sp, #8
	bl CreateSmoke
	ldr r0, [r7, #0x54]
	ldr r2, _080D1A50 @ =0xFFFFF800
	mov sb, r2
	add r0, sb
	str r0, [sp, #8]
	ldr r0, [r7, #0x58]
	movs r3, #0x80
	lsls r3, r3, #5
	adds r0, r0, r3
	str r0, [sp, #0xc]
	movs r0, #3
	add r1, sp, #8
	bl CreateSmoke
	ldrb r0, [r7, #0x11]
	cmp r0, #2
	bne _080D1976
	ldr r0, [r7, #0x54]
	str r0, [sp, #8]
	ldr r0, [r7, #0x68]
	str r0, [sp, #0xc]
	movs r0, #1
	add r1, sp, #8
	bl CreateSmoke
_080D1976:
	ldr r2, [r7, #0x54]
	ldr r4, _080D1A4C @ =0xFFFFF000
	adds r2, r2, r4
	ldr r3, [r7, #0x68]
	add r3, sb
	mov ip, r3
	ldr r0, _080D1A54 @ =RNG_0202f388
	mov r8, r0
	ldr r0, [r0]
	ldr r6, _080D1A58 @ =0x000343FD
	muls r0, r6, r0
	ldr r4, _080D1A5C @ =0x00269EC3
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	lsrs r0, r0, #0x11
	movs r5, #7
	ands r0, r5
	subs r0, #6
	lsls r0, r0, #8
	str r0, [sp]
	adds r0, r1, #0
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	mov r3, r8
	str r1, [r3]
	lsrs r0, r0, #0x11
	ands r0, r5
	rsbs r0, r0, #0
	lsls r0, r0, #7
	str r0, [sp, #4]
	movs r0, #1
	movs r1, #3
	mov r3, ip
	bl FUN_080c5684
	ldr r2, [r7, #0x54]
	add r2, sb
	ldr r3, [r7, #0x68]
	add r3, sb
	mov ip, r3
	mov r1, r8
	ldr r0, [r1]
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	lsrs r0, r0, #0x11
	ands r0, r5
	subs r0, #6
	lsls r0, r0, #8
	str r0, [sp]
	adds r0, r1, #0
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	mov r3, r8
	str r1, [r3]
	lsrs r0, r0, #0x11
	ands r0, r5
	rsbs r0, r0, #0
	lsls r0, r0, #7
	str r0, [sp, #4]
	movs r0, #1
	movs r1, #5
	mov r3, ip
	bl FUN_080c5684
	ldr r2, [r7, #0x54]
	add r2, sb
	ldr r3, [r7, #0x68]
	movs r0, #0x80
	lsls r0, r0, #4
	adds r3, r3, r0
	mov r1, r8
	ldr r0, [r1]
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	lsrs r0, r0, #0x11
	ands r0, r5
	subs r0, #6
	lsls r0, r0, #8
	str r0, [sp]
	adds r0, r1, #0
	muls r0, r6, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	mov r4, r8
	str r1, [r4]
	lsrs r0, r0, #0x11
	ands r0, r5
	rsbs r0, r0, #0
	lsls r0, r0, #7
	str r0, [sp, #4]
	movs r0, #1
	movs r1, #4
	bl FUN_080c5684
	movs r0, #3
	strb r0, [r7, #0xd]
	b _080D1CD8
	.align 2, 0
_080D1A4C: .4byte 0xFFFFF000
_080D1A50: .4byte 0xFFFFF800
_080D1A54: .4byte RNG_0202f388
_080D1A58: .4byte 0x000343FD
_080D1A5C: .4byte 0x00269EC3
_080D1A60:
	ldr r0, [r7, #0x54]
	str r0, [sp, #8]
	ldr r1, [r7, #0x58]
	movs r2, #0x80
	lsls r2, r2, #5
	adds r1, r1, r2
	str r1, [sp, #0xc]
	bl PushoutToUp2
	cmp r0, #0
	beq _080D1ADA
	ldr r0, [r7, #0x54]
	ldr r3, _080D1AF8 @ =0xFFFFF800
	adds r0, r0, r3
	str r0, [sp, #8]
	ldr r0, [r7, #0x58]
	movs r4, #0x80
	lsls r4, r4, #5
	adds r0, r0, r4
	str r0, [sp, #0xc]
	movs r0, #3
	add r1, sp, #8
	bl CreateSmoke
	ldr r0, [sp, #8]
	adds r0, r0, r4
	str r0, [sp, #8]
	movs r0, #3
	add r1, sp, #8
	bl CreateSmoke
	movs r0, #0x41
	bl isSoundPlaying
	cmp r0, #0
	bne _080D1AAE
	movs r0, #0x41
	bl PlaySound
_080D1AAE:
	adds r0, r7, #0
	adds r0, #0x8c
	movs r4, #0
	str r4, [r0]
	adds r0, #4
	str r4, [r0]
	adds r0, #4
	strb r4, [r0]
	ldrb r1, [r7, #0xa]
	movs r0, #0xfb
	ands r0, r1
	strb r0, [r7, #0xa]
	str r4, [r7, #0x60]
	adds r1, r7, #0
	adds r1, #0x54
	movs r0, #2
	bl AppendQuake
	strb r4, [r7, #0x13]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D1ADA:
	ldrb r0, [r7, #0xd]
	cmp r0, #2
	bne _080D1B0C
	ldrb r1, [r7, #0x13]
	adds r0, r1, #1
	strb r0, [r7, #0x13]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	beq _080D1AFC
	ldrb r1, [r7, #0xa]
	movs r0, #0xfe
	ands r0, r1
	b _080D1B02
	.align 2, 0
_080D1AF8: .4byte 0xFFFFF800
_080D1AFC:
	ldrb r0, [r7, #0xa]
	movs r1, #1
	orrs r0, r1
_080D1B02:
	strb r0, [r7, #0xa]
	ldr r0, [r7, #0x54]
	ldr r1, [r7, #0x5c]
	adds r0, r0, r1
	str r0, [r7, #0x54]
_080D1B0C:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r1, [r7, #0x60]
	ldr r0, _080D1B80 @ =0x000006FF
	cmp r1, r0
	bgt _080D1B20
	adds r0, r1, #0
	adds r0, #0x2a
	str r0, [r7, #0x60]
_080D1B20:
	ldr r1, [r7, #0x60]
	cmp r1, #0
	ble _080D1B2C
	ldr r0, [r7, #0x58]
	adds r0, r0, r1
	str r0, [r7, #0x58]
_080D1B2C:
	ldr r0, _080D1B84 @ =gStageRun+232
	adds r1, r7, #0
	adds r1, #0x54
	bl Camera_GetDistance
	movs r1, #0xc0
	lsls r1, r1, #6
	cmp r0, r1
	bls _080D1B78
	ldrb r1, [r7, #0xa]
	movs r0, #0xfe
	ands r0, r1
	movs r1, #0
	strb r0, [r7, #0xa]
	adds r0, r7, #0
	adds r0, #0x8c
	str r1, [r0]
	adds r0, #4
	str r1, [r0]
	adds r0, #4
	strb r1, [r0]
	ldrb r1, [r7, #0xa]
	movs r0, #0xfb
	ands r0, r1
	strb r0, [r7, #0xa]
	ldrb r1, [r7, #0xb]
	movs r0, #0xf7
	ands r0, r1
	strb r0, [r7, #0xb]
	ldr r1, _080D1B88 @ =gSolidFnTable
	ldrb r0, [r7, #9]
	lsls r0, r0, #2
	adds r0, r0, r1
	movs r1, #4
	str r1, [r7, #0xc]
	ldr r0, [r0]
	ldr r0, [r0, #0x10]
	str r0, [r7, #0x14]
_080D1B78:
	adds r0, r7, #0
	bl UpdateEntityAnim
	b _080D1CD8
	.align 2, 0
_080D1B80: .4byte 0x000006FF
_080D1B84: .4byte gStageRun+232
_080D1B88: .4byte gSolidFnTable
_080D1B8C:
	ldr r0, [r7, #0x54]
	str r0, [sp, #8]
	ldr r1, [r7, #0x58]
	movs r2, #0x80
	lsls r2, r2, #4
	adds r1, r1, r2
	str r1, [sp, #0xc]
	bl PushoutToUp2
	cmp r0, #0
	beq _080D1C1E
	ldr r0, [r7, #0x54]
	ldr r3, _080D1C3C @ =0xFFFFF800
	adds r0, r0, r3
	str r0, [sp, #8]
	ldr r0, [r7, #0x58]
	movs r4, #0x80
	lsls r4, r4, #5
	adds r0, r0, r4
	str r0, [sp, #0xc]
	movs r0, #3
	add r1, sp, #8
	bl CreateSmoke
	ldr r0, [sp, #8]
	adds r0, r0, r4
	str r0, [sp, #8]
	movs r0, #3
	add r1, sp, #8
	bl CreateSmoke
	adds r0, r7, #0
	adds r0, #0x8c
	movs r4, #0
	str r4, [r0]
	adds r0, #4
	str r4, [r0]
	adds r0, #4
	strb r4, [r0]
	ldrb r1, [r7, #0xa]
	movs r0, #0xfb
	ands r0, r1
	strb r0, [r7, #0xa]
	ldr r0, [r7, #0x60]
	rsbs r0, r0, #0
	asrs r0, r0, #1
	str r0, [r7, #0x60]
	ldr r0, [r7, #0x5c]
	asrs r0, r0, #1
	str r0, [r7, #0x5c]
	ldr r2, _080D1C40 @ =RNG_0202f388
	ldr r1, [r2]
	ldr r0, _080D1C44 @ =0x000343FD
	muls r0, r1, r0
	ldr r1, _080D1C48 @ =0x00269EC3
	adds r0, r0, r1
	lsls r0, r0, #1
	lsrs r1, r0, #1
	str r1, [r2]
	lsrs r0, r0, #0x11
	movs r1, #0xf
	ands r0, r1
	subs r0, #7
	strb r0, [r7, #0x12]
	adds r1, r7, #0
	adds r1, #0x54
	movs r0, #2
	bl AppendQuake
	strb r4, [r7, #0x13]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D1C1E:
	ldrb r0, [r7, #0xd]
	cmp r0, #4
	bne _080D1C54
	ldrb r1, [r7, #0x13]
	adds r0, r1, #1
	strb r0, [r7, #0x13]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	beq _080D1C4C
	ldrb r1, [r7, #0xa]
	movs r0, #0xfe
	ands r0, r1
	b _080D1C52
	.align 2, 0
_080D1C3C: .4byte 0xFFFFF800
_080D1C40: .4byte RNG_0202f388
_080D1C44: .4byte 0x000343FD
_080D1C48: .4byte 0x00269EC3
_080D1C4C:
	ldrb r0, [r7, #0xa]
	movs r1, #1
	orrs r0, r1
_080D1C52:
	strb r0, [r7, #0xa]
_080D1C54:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r1, [r7, #0x60]
	ldr r0, _080D1CE8 @ =0x000006FF
	cmp r1, r0
	bgt _080D1C68
	adds r0, r1, #0
	adds r0, #0x2a
	str r0, [r7, #0x60]
_080D1C68:
	ldr r1, [r7, #0x60]
	cmp r1, #0
	ble _080D1C74
	ldr r0, [r7, #0x58]
	adds r0, r0, r1
	str r0, [r7, #0x58]
_080D1C74:
	ldr r0, [r7, #0x54]
	ldr r1, [r7, #0x5c]
	adds r0, r0, r1
	str r0, [r7, #0x54]
	adds r1, r7, #0
	adds r1, #0x24
	ldrb r0, [r7, #0x12]
	ldrb r2, [r1]
	adds r0, r0, r2
	movs r4, #0
	strb r0, [r1]
	ldr r0, _080D1CEC @ =gStageRun+232
	adds r1, #0x30
	bl Camera_GetDistance
	movs r1, #0xc0
	lsls r1, r1, #6
	cmp r0, r1
	bls _080D1CD2
	ldrb r1, [r7, #0xa]
	movs r0, #0xfe
	ands r0, r1
	strb r0, [r7, #0xa]
	adds r0, r7, #0
	adds r0, #0x8c
	str r4, [r0]
	adds r0, #4
	str r4, [r0]
	adds r0, #4
	strb r4, [r0]
	ldrb r1, [r7, #0xa]
	movs r0, #0xfb
	ands r0, r1
	strb r0, [r7, #0xa]
	ldrb r1, [r7, #0xb]
	movs r0, #0xf7
	ands r0, r1
	strb r0, [r7, #0xb]
	ldr r1, _080D1CF0 @ =gSolidFnTable
	ldrb r0, [r7, #9]
	lsls r0, r0, #2
	adds r0, r0, r1
	movs r1, #4
	str r1, [r7, #0xc]
	ldr r0, [r0]
	ldr r0, [r0, #0x10]
	str r0, [r7, #0x14]
_080D1CD2:
	adds r0, r7, #0
	bl UpdateEntityAnim
_080D1CD8:
	add sp, #0x10
	pop {r3, r4}
	mov r8, r3
	mov sb, r4
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0
	.align 2, 0
_080D1CE8: .4byte 0x000006FF
_080D1CEC: .4byte gStageRun+232
_080D1CF0: .4byte gSolidFnTable

	thumb_func_start ActorCrashedPantheon_Update
ActorCrashedPantheon_Update: @ 0x080D1CF4
	push {r4, r5, r6, r7, lr}
	mov r7, r8
	push {r7}
	sub sp, #0xc
	adds r7, r0, #0
	ldrb r5, [r7, #0xd]
	cmp r5, #1
	beq _080D1D90
	cmp r5, #1
	bgt _080D1D0E
	cmp r5, #0
	beq _080D1D14
	b _080D1EF2
_080D1D0E:
	cmp r5, #2
	beq _080D1DD0
	b _080D1EF2
_080D1D14:
	ldr r0, _080D1DB4 @ =wStaticGraphicTilenums
	movs r2, #0xa1
	lsls r2, r2, #2
	strh r2, [r0, #0x26]
	ldr r6, _080D1DB8 @ =wStaticMotionPalIDs
	movs r0, #5
	strh r0, [r6, #0x26]
	ldrb r0, [r7, #0x11]
	cmp r0, #0
	bne _080D1D5A
	movs r4, #0xbe
	lsls r4, r4, #1
	ldr r1, _080D1DBC @ =gStaticMotionGraphics
	adds r0, r4, r1
	ldrh r1, [r0, #6]
	lsrs r1, r1, #6
	subs r1, r2, r1
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r3, _080D1DC0 @ =gStaticMotionGraphics+12
	adds r4, r4, r3
	ldrh r1, [r6, #0x26]
	ldrb r0, [r4, #7]
	subs r1, r1, r0
	lsls r1, r1, #5
	movs r0, #0x80
	lsls r0, r0, #2
	adds r1, r1, r0
	adds r0, r4, #0
	bl LoadPalette
_080D1D5A:
	ldr r0, [r7, #0x54]
	ldr r1, [r7, #0x58]
	bl FUN_08009f6c
	str r0, [r7, #0x58]
	ldr r1, _080D1DC4 @ =0x00001301
	adds r0, r7, #0
	bl SetMotion
	ldrb r1, [r7, #0xa]
	movs r0, #4
	orrs r0, r1
	strb r0, [r7, #0xa]
	adds r4, r7, #0
	adds r4, #0x74
	ldr r1, _080D1DC8 @ =Collision_08370ad0
	adds r2, r7, #0
	adds r2, #0x54
	adds r0, r4, #0
	movs r3, #0
	bl InitBody
	str r7, [r4, #0x2c]
	str r5, [r4, #0x24]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D1D90:
	adds r0, r7, #0
	bl UpdateEntityAnim
	adds r0, r7, #0
	adds r0, #0x8c
	ldr r0, [r0]
	movs r1, #0x80
	lsls r1, r1, #2
	ands r0, r1
	cmp r0, #0
	bne _080D1DA8
	b _080D1EF2
_080D1DA8:
	ldr r1, _080D1DCC @ =0x00001303
	adds r0, r7, #0
	bl SetMotion
	b _080D1EEC
	.align 2, 0
_080D1DB4: .4byte wStaticGraphicTilenums
_080D1DB8: .4byte wStaticMotionPalIDs
_080D1DBC: .4byte gStaticMotionGraphics
_080D1DC0: .4byte gStaticMotionGraphics+12
_080D1DC4: .4byte 0x00001301
_080D1DC8: .4byte Collision_08370ad0
_080D1DCC: .4byte 0x00001303
_080D1DD0:
	adds r0, r7, #0
	bl UpdateEntityAnim
	adds r0, r7, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	beq _080D1DE2
	b _080D1EF2
_080D1DE2:
	ldr r0, [r7, #0x54]
	str r0, [sp]
	ldr r0, [r7, #0x58]
	ldr r1, _080D1F00 @ =0xFFFFE800
	adds r0, r0, r1
	str r0, [sp, #4]
	ldr r4, _080D1F04 @ =sProloguePantheons
	ldrb r0, [r7, #0xa]
	movs r5, #0x10
	adds r3, r5, #0
	ands r3, r0
	lsls r3, r3, #0x18
	lsrs r3, r3, #0x18
	mov r0, sp
	adds r1, r4, #0
	movs r2, #0
	bl CreateSlashedEnemy
	adds r1, r4, #0
	adds r1, #0x1c
	ldrb r0, [r7, #0xa]
	adds r3, r5, #0
	ands r3, r0
	lsls r3, r3, #0x18
	lsrs r3, r3, #0x18
	mov r0, sp
	movs r2, #0
	bl CreateSlashedEnemy
	adds r4, #0x38
	ldrb r0, [r7, #0xa]
	adds r3, r5, #0
	ands r3, r0
	lsls r3, r3, #0x18
	lsrs r3, r3, #0x18
	mov r0, sp
	adds r1, r4, #0
	movs r2, #0
	bl CreateSlashedEnemy
	ldr r0, [r7, #0x58]
	ldr r2, _080D1F08 @ =0xFFFFF000
	adds r0, r0, r2
	str r0, [sp, #4]
	movs r0, #1
	mov r1, sp
	bl CreateSmoke
	ldr r3, _080D1F0C @ =RNG_0202f388
	mov r8, r3
	ldr r0, [r3]
	ldr r2, _080D1F10 @ =0x000343FD
	muls r0, r2, r0
	ldr r4, _080D1F14 @ =0x00269EC3
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r3, r0, #1
	lsrs r0, r0, #0x11
	movs r6, #0x1f
	ands r0, r6
	subs r0, r5, r0
	lsls r0, r0, #8
	ldr r1, [r7, #0x54]
	adds r1, r1, r0
	str r1, [sp]
	adds r0, r3, #0
	muls r0, r2, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	mov r3, r8
	str r1, [r3]
	lsrs r0, r0, #0x11
	ands r0, r6
	lsls r0, r0, #8
	ldr r1, [r7, #0x58]
	subs r1, r1, r0
	str r1, [sp, #4]
	movs r0, #2
	mov r1, sp
	str r2, [sp, #8]
	bl CreateSmoke
	mov r1, r8
	ldr r0, [r1]
	ldr r2, [sp, #8]
	muls r0, r2, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	lsrs r0, r0, #0x11
	ands r0, r6
	subs r5, r5, r0
	lsls r5, r5, #8
	ldr r0, [r7, #0x54]
	adds r0, r0, r5
	str r0, [sp]
	adds r0, r1, #0
	muls r0, r2, r0
	adds r0, r0, r4
	lsls r0, r0, #1
	lsrs r1, r0, #1
	mov r2, r8
	str r1, [r2]
	lsrs r0, r0, #0x11
	ands r0, r6
	lsls r0, r0, #8
	ldr r1, [r7, #0x58]
	subs r1, r1, r0
	str r1, [sp, #4]
	movs r0, #2
	mov r1, sp
	bl CreateSmoke
	movs r0, #0x2a
	bl PlaySound
	ldrb r1, [r7, #0xa]
	movs r0, #0xfe
	ands r0, r1
	movs r1, #0
	strb r0, [r7, #0xa]
	adds r0, r7, #0
	adds r0, #0x8c
	str r1, [r0]
	adds r0, #4
	str r1, [r0]
	adds r0, #4
	strb r1, [r0]
	ldrb r1, [r7, #0xa]
	movs r0, #0xfb
	ands r0, r1
	strb r0, [r7, #0xa]
_080D1EEC:
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D1EF2:
	add sp, #0xc
	pop {r3}
	mov r8, r3
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0
	.align 2, 0
_080D1F00: .4byte 0xFFFFE800
_080D1F04: .4byte sProloguePantheons
_080D1F08: .4byte 0xFFFFF000
_080D1F0C: .4byte RNG_0202f388
_080D1F10: .4byte 0x000343FD
_080D1F14: .4byte 0x00269EC3

	thumb_func_start Actor10_Update
Actor10_Update: @ 0x080D1F18
	push {r4, r5, r6, lr}
	adds r6, r0, #0
	ldrb r0, [r6, #0xd]
	cmp r0, #8
	bls _080D1F24
	b _080D21E8
_080D1F24:
	lsls r0, r0, #2
	ldr r1, _080D1F30 @ =_080D1F34
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D1F30: .4byte _080D1F34
_080D1F34: @ jump table
	.4byte _080D1F58 @ case 0
	.4byte _080D1FDE @ case 1
	.4byte _080D2024 @ case 2
	.4byte _080D203E @ case 3
	.4byte _080D2054 @ case 4
	.4byte _080D2064 @ case 5
	.4byte _080D2114 @ case 6
	.4byte _080D2180 @ case 7
	.4byte _080D21E8 @ case 8
_080D1F58:
	ldr r0, _080D2004 @ =0x085D79AC
	ldr r1, _080D2008 @ =wStaticGraphicTilenums
	ldrh r1, [r1, #0x12]
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r0, _080D200C @ =gStaticMotionGraphics+((20*9)+12)
	ldr r1, _080D2010 @ =wStaticMotionPalIDs
	ldrh r1, [r1, #0x12]
	ldrb r2, [r0, #7]
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #2
	adds r1, r1, r2
	bl LoadPalette
	adds r0, r6, #0
	bl InitRotatableMotion
	ldr r1, _080D2014 @ =0x00000902
	adds r0, r6, #0
	bl SetMotion
	adds r1, r6, #0
	adds r1, #0x24
	movs r0, #0x40
	strb r0, [r1]
	movs r2, #1
	ldrb r1, [r6, #0xa]
	movs r0, #0x20
	orrs r0, r1
	strb r0, [r6, #0xa]
	adds r0, r6, #0
	adds r0, #0x4d
	strb r2, [r0]
	adds r3, r6, #0
	adds r3, #0x4a
	movs r2, #0x20
	ldrb r1, [r3]
	movs r0, #0x21
	rsbs r0, r0, #0
	ands r0, r1
	orrs r0, r2
	strb r0, [r3]
	ldr r0, [r6, #0x54]
	ldr r1, [r6, #0x58]
	bl FUN_0800a31c
	movs r1, #0xe0
	lsls r1, r1, #5
	adds r0, r0, r1
	str r0, [r6, #0x64]
	ldr r0, _080D2018 @ =gStageRun+232
	ldr r0, [r0, #0x38]
	ldr r2, _080D201C @ =0x00009BFF
	adds r0, r0, r2
	str r0, [r6, #0x54]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D1FDE:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r0, [r6, #0x54]
	ldr r1, _080D2020 @ =0xFFFFF800
	adds r0, r0, r1
	str r0, [r6, #0x54]
	ldr r1, [r6, #0x64]
	cmp r0, r1
	blt _080D1FF4
	b _080D21E8
_080D1FF4:
	adds r1, r6, #0
	adds r1, #0x54
	movs r0, #0x10
	bl AppendQuake
	ldr r0, [r6, #0x64]
	str r0, [r6, #0x54]
	b _080D21E2
	.align 2, 0
_080D2004: .4byte gStaticMotionGraphics+(20*9)
_080D2008: .4byte wStaticGraphicTilenums
_080D200C: .4byte gStaticMotionGraphics+(20*9)+12
_080D2010: .4byte wStaticMotionPalIDs
_080D2014: .4byte 0x00000902
_080D2018: .4byte gStageRun+232
_080D201C: .4byte 0x00009BFF
_080D2020: .4byte 0xFFFFF800
_080D2024:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r0, [r6, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	bne _080D2038
	b _080D21E8
_080D2038:
	movs r0, #0x1e
	strb r0, [r6, #0x12]
	b _080D21E2
_080D203E:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldrb r0, [r6, #0x12]
	subs r0, #1
	strb r0, [r6, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	beq _080D2052
	b _080D21E8
_080D2052:
	b _080D21E2
_080D2054:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r1, [r6, #0x54]
	movs r2, #0x80
	lsls r2, r2, #2
	adds r1, r1, r2
	b _080D21CC
_080D2064:
	ldr r0, [r6, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #2
	ands r0, r1
	cmp r0, #0
	bne _080D2072
	b _080D21E8
_080D2072:
	ldrb r1, [r6, #0xa]
	movs r0, #1
	orrs r0, r1
	strb r0, [r6, #0xa]
	ldr r0, _080D2154 @ =0x085D79AC
	ldr r1, _080D2158 @ =wStaticGraphicTilenums
	ldrh r1, [r1, #0x12]
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r0, _080D215C @ =gStaticMotionGraphics+((20*9)+12)
	ldr r1, _080D2160 @ =wStaticMotionPalIDs
	ldrh r1, [r1, #0x12]
	ldrb r2, [r0, #7]
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #2
	adds r1, r1, r2
	bl LoadPalette
	ldr r1, _080D2164 @ =0x00000902
	adds r0, r6, #0
	bl SetMotion
	adds r1, r6, #0
	adds r1, #0x24
	movs r0, #0x20
	strb r0, [r1]
	movs r5, #0
	ldrb r1, [r6, #0xa]
	movs r0, #0xdf
	ands r0, r1
	strb r0, [r6, #0xa]
	adds r0, r6, #0
	adds r0, #0x4d
	strb r5, [r0]
	adds r2, r6, #0
	adds r2, #0x4a
	ldrb r1, [r2]
	movs r0, #0x21
	rsbs r0, r0, #0
	ands r0, r1
	strb r0, [r2]
	ldrb r1, [r6, #0xa]
	movs r0, #4
	orrs r0, r1
	strb r0, [r6, #0xa]
	adds r4, r6, #0
	adds r4, #0x74
	ldr r1, _080D2168 @ =sCollisions_08370B58
	adds r2, #0xa
	adds r0, r4, #0
	movs r3, #1
	bl InitBody
	str r6, [r4, #0x2c]
	str r5, [r4, #0x24]
	ldr r0, _080D216C @ =gStageRun+232
	ldr r0, [r0, #0x38]
	ldr r2, _080D2170 @ =0x000097FF
	adds r1, r0, r2
	str r1, [r6, #0x54]
	ldr r1, _080D2174 @ =0x00001FFF
	adds r0, r0, r1
	ldr r1, [r6, #0x58]
	bl FUN_08009f6c
	str r0, [r6, #0x68]
	ldr r2, _080D2178 @ =0xFFFFD000
	adds r0, r0, r2
	str r0, [r6, #0x58]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D2114:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r0, [r6, #0x54]
	ldr r1, _080D217C @ =0xFFFFFA00
	adds r0, r0, r1
	str r0, [r6, #0x54]
	ldr r1, [r6, #0x58]
	lsls r0, r1, #6
	subs r0, r0, r1
	ldr r1, [r6, #0x68]
	adds r0, r0, r1
	asrs r0, r0, #6
	str r0, [r6, #0x58]
	adds r0, r6, #0
	adds r0, #0x8c
	ldr r0, [r0]
	movs r1, #4
	ands r0, r1
	cmp r0, #0
	beq _080D21E8
	adds r1, r6, #0
	adds r1, #0x54
	movs r0, #4
	bl AppendQuake
	movs r0, #0
	str r0, [r6, #0x5c]
	movs r0, #0xf
	strb r0, [r6, #0x12]
	b _080D21E2
	.align 2, 0
_080D2154: .4byte gStaticMotionGraphics+(20*9)
_080D2158: .4byte wStaticGraphicTilenums
_080D215C: .4byte gStaticMotionGraphics+((20*9)+12)
_080D2160: .4byte wStaticMotionPalIDs
_080D2164: .4byte 0x00000902
_080D2168: .4byte sCollisions_08370B58
_080D216C: .4byte gStageRun+232
_080D2170: .4byte 0x000097FF
_080D2174: .4byte 0x00001FFF
_080D2178: .4byte 0xFFFFD000
_080D217C: .4byte 0xFFFFFA00
_080D2180:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r1, [r6, #0x58]
	lsls r0, r1, #6
	subs r0, r0, r1
	ldr r2, _080D21B4 @ =0xFFFFD000
	adds r0, r0, r2
	ldr r1, [r6, #0x68]
	adds r0, r0, r1
	asrs r0, r0, #6
	str r0, [r6, #0x58]
	adds r2, r6, #0
	adds r2, #0x24
	ldrb r1, [r2]
	lsls r0, r1, #4
	subs r0, r0, r1
	adds r0, #0x4f
	asrs r0, r0, #4
	strb r0, [r2]
	ldrb r0, [r6, #0x12]
	cmp r0, #0
	beq _080D21B8
	subs r0, #1
	strb r0, [r6, #0x12]
	b _080D21E8
	.align 2, 0
_080D21B4: .4byte 0xFFFFD000
_080D21B8:
	ldr r1, [r6, #0x5c]
	lsls r0, r1, #5
	subs r0, r0, r1
	movs r1, #0xc0
	lsls r1, r1, #3
	adds r0, r0, r1
	asrs r0, r0, #5
	str r0, [r6, #0x5c]
	ldr r1, [r6, #0x54]
	adds r1, r1, r0
_080D21CC:
	str r1, [r6, #0x54]
	ldr r0, _080D21F0 @ =gStageRun+232
	ldr r0, [r0, #0x38]
	ldr r2, _080D21F4 @ =0x000097FF
	adds r0, r0, r2
	cmp r1, r0
	blt _080D21E8
	ldrb r0, [r6, #0xa]
	movs r1, #0xfe
	ands r1, r0
	strb r1, [r6, #0xa]
_080D21E2:
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D21E8:
	pop {r4, r5, r6}
	pop {r0}
	bx r0
	.align 2, 0
_080D21F0: .4byte gStageRun+232
_080D21F4: .4byte 0x000097FF

	thumb_func_start ActorLeviathan11_Update
ActorLeviathan11_Update: @ 0x080D21F8
	push {r4, r5, r6, lr}
	adds r6, r0, #0
	ldrb r0, [r6, #0xd]
	cmp r0, #7
	bls _080D2204
	b _080D23A6
_080D2204:
	lsls r0, r0, #2
	ldr r1, _080D2210 @ =_080D2214
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D2210: .4byte _080D2214
_080D2214: @ jump table
	.4byte _080D2234 @ case 0
	.4byte _080D22B4 @ case 1
	.4byte _080D22F8 @ case 2
	.4byte _080D2318 @ case 3
	.4byte _080D232E @ case 4
	.4byte _080D2380 @ case 5
	.4byte _080D2390 @ case 6
	.4byte _080D23A6 @ case 7
_080D2234:
	ldr r2, _080D22DC @ =wDynamicGraphicTilenums
	movs r0, #0xbd
	lsls r0, r0, #1
	adds r2, r2, r0
	ldr r1, _080D22E0 @ =wDynamicMotionPalIDs
	adds r1, r1, r0
	movs r3, #8
	movs r0, #0xf3
	lsls r0, r0, #2
	strh r0, [r2]
	strh r3, [r1]
	ldr r1, _080D22E4 @ =0x0000BD10
	adds r0, r6, #0
	bl SetMotion
	movs r2, #1
	ldrb r1, [r6, #0xa]
	movs r0, #0x10
	orrs r0, r1
	strb r0, [r6, #0xa]
	adds r0, r6, #0
	adds r0, #0x4c
	movs r5, #0
	strb r2, [r0]
	adds r3, r6, #0
	adds r3, #0x4a
	movs r2, #0x10
	ldrb r1, [r3]
	movs r0, #0x11
	rsbs r0, r0, #0
	ands r0, r1
	orrs r0, r2
	strb r0, [r3]
	ldrb r1, [r6, #0xa]
	movs r0, #4
	orrs r0, r1
	strb r0, [r6, #0xa]
	adds r4, r6, #0
	adds r4, #0x74
	ldr r1, _080D22E8 @ =sCollisions_08370B58+(24*1)
	adds r2, r6, #0
	adds r2, #0x54
	adds r0, r4, #0
	movs r3, #9
	bl InitBody
	str r6, [r4, #0x2c]
	str r5, [r4, #0x24]
	ldr r0, [r6, #0x54]
	ldr r1, [r6, #0x58]
	bl FUN_0800a31c
	movs r1, #0x80
	lsls r1, r1, #4
	adds r0, r0, r1
	str r0, [r6, #0x64]
	ldr r0, _080D22EC @ =gStageRun+232
	ldr r0, [r0, #0x38]
	ldr r2, _080D22F0 @ =0x000087FF
	adds r0, r0, r2
	str r0, [r6, #0x54]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D22B4:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r0, [r6, #0x54]
	ldr r1, _080D22F4 @ =0xFFFFF800
	adds r0, r0, r1
	str r0, [r6, #0x54]
	ldr r1, [r6, #0x64]
	cmp r0, r1
	bge _080D23A6
	movs r0, #0x56
	bl PlaySound
	ldr r0, [r6, #0x64]
	str r0, [r6, #0x54]
	adds r1, r6, #0
	adds r1, #0x94
	movs r0, #0x5a
	strb r0, [r1]
	b _080D23A0
	.align 2, 0
_080D22DC: .4byte wDynamicGraphicTilenums
_080D22E0: .4byte wDynamicMotionPalIDs
_080D22E4: .4byte 0x0000BD10
_080D22E8: .4byte sCollisions_08370B58+(24*1)
_080D22EC: .4byte gStageRun+232
_080D22F0: .4byte 0x000087FF
_080D22F4: .4byte 0xFFFFF800
_080D22F8:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r0, [r6, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	beq _080D23A6
	ldr r1, _080D2314 @ =0x0000BD12
	adds r0, r6, #0
	bl SetMotion
	b _080D23A0
	.align 2, 0
_080D2314: .4byte 0x0000BD12
_080D2318:
	adds r0, r6, #0
	bl UpdateEntityAnim
	adds r0, r6, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	bne _080D23A6
	movs r0, #0
	str r0, [r6, #0x60]
	b _080D23A0
_080D232E:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r1, [r6, #0x60]
	ldr r0, _080D2374 @ =0x000006FF
	cmp r1, r0
	bgt _080D2342
	adds r0, r1, #0
	adds r0, #0x2a
	str r0, [r6, #0x60]
_080D2342:
	ldr r1, [r6, #0x58]
	ldr r0, [r6, #0x60]
	adds r1, r1, r0
	str r1, [r6, #0x58]
	ldr r0, [r6, #0x54]
	movs r2, #0xc0
	lsls r2, r2, #3
	adds r1, r1, r2
	bl PushoutToUp2
	cmp r0, #0
	beq _080D23A6
	ldr r0, [r6, #0x54]
	ldr r1, [r6, #0x58]
	bl FUN_08009f6c
	ldr r1, _080D2378 @ =0xFFFFFA00
	adds r0, r0, r1
	str r0, [r6, #0x58]
	ldr r1, _080D237C @ =0x0000BD1B
	adds r0, r6, #0
	bl SetMotion
	b _080D23A0
	.align 2, 0
_080D2374: .4byte 0x000006FF
_080D2378: .4byte 0xFFFFFA00
_080D237C: .4byte 0x0000BD1B
_080D2380:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r0, [r6, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #2
	ands r0, r1
	b _080D239C
_080D2390:
	ldr r1, _080D23AC @ =0x0000BD1B
	adds r0, r6, #0
	movs r2, #1
	bl FUN_080d0934
	lsls r0, r0, #0x10
_080D239C:
	cmp r0, #0
	beq _080D23A6
_080D23A0:
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D23A6:
	pop {r4, r5, r6}
	pop {r0}
	bx r0
	.align 2, 0
_080D23AC: .4byte 0x0000BD1B

	thumb_func_start ActorFefnir12_Update
ActorFefnir12_Update: @ 0x080D23B0
	push {r4, r5, r6, r7, lr}
	sub sp, #8
	adds r7, r0, #0
	ldrb r0, [r7, #0xd]
	cmp r0, #0x14
	bls _080D23BE
	b _080D27FC
_080D23BE:
	lsls r0, r0, #2
	ldr r1, _080D23C8 @ =_080D23CC
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D23C8: .4byte _080D23CC
_080D23CC: @ jump table
	.4byte _080D2420 @ case 0
	.4byte _080D24A0 @ case 1
	.4byte _080D24EC @ case 2
	.4byte _080D2558 @ case 3
	.4byte _080D25B0 @ case 4
	.4byte _080D25D8 @ case 5
	.4byte _080D264C @ case 6
	.4byte _080D2688 @ case 7
	.4byte _080D264C @ case 8
	.4byte _080D2688 @ case 9
	.4byte _080D264C @ case 10
	.4byte _080D2688 @ case 11
	.4byte _080D269C @ case 12
	.4byte _080D27FC @ case 13
	.4byte _080D26B0 @ case 14
	.4byte _080D26E4 @ case 15
	.4byte _080D2750 @ case 16
	.4byte _080D27A8 @ case 17
	.4byte _080D27C8 @ case 18
	.4byte _080D27E4 @ case 19
	.4byte _080D27FC @ case 20
_080D2420:
	ldr r0, _080D24CC @ =wDynamicGraphicTilenums
	movs r2, #0xa1
	lsls r2, r2, #1
	adds r0, r0, r2
	ldr r1, _080D24D0 @ =0x0000034D
	strh r1, [r0]
	ldr r0, _080D24D4 @ =wDynamicMotionPalIDs
	adds r0, r0, r2
	movs r1, #9
	strh r1, [r0]
	ldr r1, _080D24D8 @ =0x0000A114
	adds r0, r7, #0
	bl SetMotion
	movs r2, #1
	ldrb r1, [r7, #0xa]
	movs r0, #0x10
	orrs r0, r1
	strb r0, [r7, #0xa]
	adds r0, r7, #0
	adds r0, #0x4c
	movs r5, #0
	strb r2, [r0]
	adds r3, r7, #0
	adds r3, #0x4a
	movs r2, #0x10
	ldrb r1, [r3]
	movs r0, #0x11
	rsbs r0, r0, #0
	ands r0, r1
	orrs r0, r2
	strb r0, [r3]
	ldrb r1, [r7, #0xa]
	movs r0, #4
	orrs r0, r1
	strb r0, [r7, #0xa]
	adds r4, r7, #0
	adds r4, #0x74
	ldr r1, _080D24DC @ =sCollisions_08370B58+(24*1)
	adds r2, r7, #0
	adds r2, #0x54
	adds r0, r4, #0
	movs r3, #9
	bl InitBody
	str r7, [r4, #0x2c]
	str r5, [r4, #0x24]
	adds r1, r7, #0
	adds r1, #0x94
	movs r0, #0x5a
	strb r0, [r1]
	movs r0, #0xf4
	bl PlaySound
	ldr r0, _080D24E0 @ =gStageRun+232
	ldr r0, [r0, #0x38]
	ldr r1, _080D24E4 @ =0x000087FF
	adds r0, r0, r1
	str r0, [r7, #0x54]
	movs r0, #0x14
	strb r0, [r7, #0x12]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D24A0:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r0, [r7, #0x54]
	ldr r2, _080D24E8 @ =0xFFFFFD00
	adds r0, r0, r2
	str r0, [r7, #0x54]
	ldrb r0, [r7, #0x12]
	subs r0, #1
	strb r0, [r7, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	beq _080D24BC
	b _080D27FC
_080D24BC:
	movs r0, #8
	strb r0, [r7, #0x12]
	movs r1, #0xa1
	lsls r1, r1, #8
	adds r0, r7, #0
	bl SetMotion
	b _080D27F6
	.align 2, 0
_080D24CC: .4byte wDynamicGraphicTilenums
_080D24D0: .4byte 0x0000034D
_080D24D4: .4byte wDynamicMotionPalIDs
_080D24D8: .4byte 0x0000A114
_080D24DC: .4byte sCollisions_08370B58+(24*1)
_080D24E0: .4byte gStageRun+232
_080D24E4: .4byte 0x000087FF
_080D24E8: .4byte 0xFFFFFD00
_080D24EC:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r2, [r7, #0x54]
	ldr r1, _080D254C @ =0xFFFFFE00
	adds r0, r2, r1
	str r0, [r7, #0x54]
	ldrb r1, [r7, #0x12]
	movs r0, #3
	ands r0, r1
	cmp r0, #0
	bne _080D2528
	ldr r1, _080D2550 @ =0xFFFFF200
	adds r0, r2, r1
	str r0, [sp]
	ldr r0, [r7, #0x58]
	str r0, [sp, #4]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
	ldr r0, [r7, #0x54]
	movs r2, #0x80
	lsls r2, r2, #4
	adds r0, r0, r2
	str r0, [sp]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
_080D2528:
	ldrb r0, [r7, #0x12]
	subs r0, #1
	strb r0, [r7, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	beq _080D2536
	b _080D27FC
_080D2536:
	ldr r1, _080D2554 @ =0x0000A11B
	adds r0, r7, #0
	bl SetMotion
	movs r0, #0x80
	lsls r0, r0, #2
	str r0, [r7, #0x5c]
	movs r0, #0x20
	strb r0, [r7, #0x12]
	b _080D27F6
	.align 2, 0
_080D254C: .4byte 0xFFFFFE00
_080D2550: .4byte 0xFFFFF200
_080D2554: .4byte 0x0000A11B
_080D2558:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r1, [r7, #0x5c]
	lsls r0, r1, #4
	subs r0, r0, r1
	asrs r0, r0, #4
	str r0, [r7, #0x5c]
	ldr r1, [r7, #0x54]
	subs r2, r1, r0
	str r2, [r7, #0x54]
	ldrb r1, [r7, #0x12]
	movs r0, #7
	ands r0, r1
	cmp r0, #0
	bne _080D259C
	ldr r1, _080D25AC @ =0xFFFFF400
	adds r0, r2, r1
	str r0, [sp]
	ldr r0, [r7, #0x58]
	str r0, [sp, #4]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
	ldr r0, [r7, #0x54]
	movs r2, #0x80
	lsls r2, r2, #4
	adds r0, r0, r2
	str r0, [sp]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
_080D259C:
	ldrb r0, [r7, #0x12]
	subs r0, #1
	strb r0, [r7, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	beq _080D25AA
	b _080D27FC
_080D25AA:
	b _080D27F6
	.align 2, 0
_080D25AC: .4byte 0xFFFFF400
_080D25B0:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r0, [r7, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	bne _080D25C4
	b _080D27FC
_080D25C4:
	ldr r1, _080D25D4 @ =0x0000A11C
	adds r0, r7, #0
	bl SetMotion
	movs r0, #0x3c
	strb r0, [r7, #0x12]
	b _080D27F6
	.align 2, 0
_080D25D4: .4byte 0x0000A11C
_080D25D8:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldrb r0, [r7, #0x12]
	subs r0, #1
	strb r0, [r7, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	beq _080D25EC
	b _080D27FC
_080D25EC:
	ldr r1, _080D2638 @ =0x0000A109
	adds r0, r7, #0
	bl SetMotion
	ldr r0, _080D263C @ =wStaticGraphicTilenums
	adds r0, #0x42
	movs r6, #0x80
	lsls r6, r6, #2
	strh r6, [r0]
	ldr r5, _080D2640 @ =wStaticMotionPalIDs
	adds r5, #0x42
	movs r0, #4
	strh r0, [r5]
	movs r4, #0xa5
	lsls r4, r4, #2
	ldr r1, _080D2644 @ =gStaticMotionGraphics
	adds r0, r4, r1
	ldrh r1, [r0, #6]
	lsrs r1, r1, #6
	subs r1, r6, r1
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r0, _080D2648 @ =gStaticMotionGraphics+12
	adds r4, r4, r0
	ldrh r1, [r5]
	ldrb r0, [r4, #7]
	subs r1, r1, r0
	lsls r1, r1, #5
	adds r1, r1, r6
	adds r0, r4, #0
	bl LoadPalette
	b _080D27F6
	.align 2, 0
_080D2638: .4byte 0x0000A109
_080D263C: .4byte wStaticGraphicTilenums
_080D2640: .4byte wStaticMotionPalIDs
_080D2644: .4byte gStaticMotionGraphics
_080D2648: .4byte gStaticMotionGraphics+12
_080D264C:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r0, [r7, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #2
	ands r0, r1
	cmp r0, #0
	bne _080D2660
	b _080D27FC
_080D2660:
	ldr r1, _080D2684 @ =0x0000A10B
	adds r0, r7, #0
	bl SetMotion
	adds r0, r7, #0
	movs r1, #0xd
	bl CreateScriptActor
	movs r0, #0xf5
	bl PlaySound
	adds r1, r7, #0
	adds r1, #0x54
	movs r0, #2
	bl AppendQuake
	b _080D27F6
	.align 2, 0
_080D2684: .4byte 0x0000A10B
_080D2688:
	adds r0, r7, #0
	bl UpdateEntityAnim
	adds r0, r7, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	beq _080D269A
	b _080D27FC
_080D269A:
	b _080D27F6
_080D269C:
	adds r0, r7, #0
	bl UpdateEntityAnim
	movs r1, #0xa1
	lsls r1, r1, #8
	adds r0, r7, #0
	bl SetMotion
	movs r0, #0xe
	b _080D27FA
_080D26B0:
	adds r0, r7, #0
	bl UpdateEntityAnim
	adds r0, r7, #0
	adds r0, #0x8c
	ldr r0, [r0]
	movs r1, #1
	ands r0, r1
	cmp r0, #0
	bne _080D26C6
	b _080D27FC
_080D26C6:
	ldr r1, _080D2740 @ =0x0000A114
	adds r0, r7, #0
	bl SetMotion
	movs r0, #0xf4
	bl PlaySound
	movs r0, #0x52
	bl PlaySound
	movs r0, #8
	strb r0, [r7, #0x12]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D26E4:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r2, [r7, #0x54]
	ldr r1, _080D2744 @ =0xFFFFFE00
	adds r0, r2, r1
	str r0, [r7, #0x54]
	ldrb r1, [r7, #0x12]
	movs r0, #3
	ands r0, r1
	cmp r0, #0
	bne _080D2720
	ldr r1, _080D2748 @ =0xFFFFF200
	adds r0, r2, r1
	str r0, [sp]
	ldr r0, [r7, #0x58]
	str r0, [sp, #4]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
	ldr r0, [r7, #0x54]
	movs r2, #0x80
	lsls r2, r2, #4
	adds r0, r0, r2
	str r0, [sp]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
_080D2720:
	ldrb r0, [r7, #0x12]
	subs r0, #1
	strb r0, [r7, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	bne _080D27FC
	ldr r1, _080D274C @ =0x0000A11B
	adds r0, r7, #0
	bl SetMotion
	movs r0, #0x80
	lsls r0, r0, #3
	str r0, [r7, #0x5c]
	movs r0, #0x18
	strb r0, [r7, #0x12]
	b _080D27F6
	.align 2, 0
_080D2740: .4byte 0x0000A114
_080D2744: .4byte 0xFFFFFE00
_080D2748: .4byte 0xFFFFF200
_080D274C: .4byte 0x0000A11B
_080D2750:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r1, [r7, #0x5c]
	lsls r0, r1, #3
	subs r0, r0, r1
	asrs r0, r0, #3
	str r0, [r7, #0x5c]
	ldr r1, [r7, #0x54]
	subs r2, r1, r0
	str r2, [r7, #0x54]
	ldrb r1, [r7, #0x12]
	movs r0, #7
	ands r0, r1
	cmp r0, #0
	bne _080D2794
	ldr r1, _080D27A4 @ =0xFFFFF400
	adds r0, r2, r1
	str r0, [sp]
	ldr r0, [r7, #0x58]
	str r0, [sp, #4]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
	ldr r0, [r7, #0x54]
	movs r2, #0x80
	lsls r2, r2, #4
	adds r0, r0, r2
	str r0, [sp]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
_080D2794:
	ldrb r0, [r7, #0x12]
	subs r0, #1
	strb r0, [r7, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	bne _080D27FC
	b _080D27F6
	.align 2, 0
_080D27A4: .4byte 0xFFFFF400
_080D27A8:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r0, [r7, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #4
	ands r0, r1
	cmp r0, #0
	beq _080D27FC
	ldr r1, _080D27C4 @ =0x0000A11C
	adds r0, r7, #0
	bl SetMotion
	b _080D27F6
	.align 2, 0
_080D27C4: .4byte 0x0000A11C
_080D27C8:
	adds r0, r7, #0
	bl UpdateEntityAnim
	adds r0, r7, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	bne _080D27FC
	movs r1, #0xa1
	lsls r1, r1, #8
	adds r0, r7, #0
	bl SetMotion
	b _080D27F6
_080D27E4:
	movs r1, #0xa1
	lsls r1, r1, #8
	adds r0, r7, #0
	movs r2, #1
	bl FUN_080d0934
	lsls r0, r0, #0x10
	cmp r0, #0
	beq _080D27FC
_080D27F6:
	ldrb r0, [r7, #0xd]
	adds r0, #1
_080D27FA:
	strb r0, [r7, #0xd]
_080D27FC:
	add sp, #8
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0

	thumb_func_start Actor13_Update
Actor13_Update: @ 0x080D2804
	push {r4, r5, lr}
	adds r4, r0, #0
	ldr r5, [r4, #0x28]
	ldrb r0, [r4, #0xd]
	cmp r0, #0
	beq _080D2816
	cmp r0, #1
	beq _080D286E
	b _080D289C
_080D2816:
	adds r0, r4, #0
	bl InitScalerotMotion1
	adds r0, r4, #0
	adds r0, #0x50
	movs r1, #0xc0
	lsls r1, r1, #1
	strh r1, [r0]
	adds r0, #2
	strh r1, [r0]
	movs r1, #0x84
	lsls r1, r1, #6
	adds r0, r4, #0
	bl SetMotion
	movs r2, #1
	ldrb r1, [r4, #0xa]
	movs r0, #0x10
	orrs r0, r1
	strb r0, [r4, #0xa]
	adds r0, r4, #0
	adds r0, #0x4c
	strb r2, [r0]
	adds r3, r4, #0
	adds r3, #0x4a
	movs r2, #0x10
	ldrb r1, [r3]
	movs r0, #0x11
	rsbs r0, r0, #0
	ands r0, r1
	orrs r0, r2
	strb r0, [r3]
	ldr r0, [r5, #0x54]
	movs r1, #0xf0
	lsls r1, r1, #5
	adds r0, r0, r1
	str r0, [r4, #0x54]
	ldr r0, [r5, #0x58]
	ldr r2, _080D28A4 @ =0xFFFFE200
	adds r0, r0, r2
	str r0, [r4, #0x58]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D286E:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldr r1, [r4, #0x54]
	movs r0, #0x80
	lsls r0, r0, #3
	adds r1, r1, r0
	str r1, [r4, #0x54]
	ldr r0, _080D28A8 @ =gStageRun+232
	ldr r0, [r0, #0x38]
	ldr r2, _080D28AC @ =0x0000B7FF
	adds r0, r0, r2
	cmp r1, r0
	ble _080D289C
	ldr r1, _080D28B0 @ =gSolidFnTable
	ldrb r0, [r4, #9]
	lsls r0, r0, #2
	adds r0, r0, r1
	movs r1, #2
	str r1, [r4, #0xc]
	ldr r0, [r0]
	ldr r0, [r0, #8]
	str r0, [r4, #0x14]
_080D289C:
	pop {r4, r5}
	pop {r0}
	bx r0
	.align 2, 0
_080D28A4: .4byte 0xFFFFE200
_080D28A8: .4byte gStageRun+232
_080D28AC: .4byte 0x0000B7FF
_080D28B0: .4byte gSolidFnTable

	thumb_func_start ActorSaveSelectCiel_Update
ActorSaveSelectCiel_Update: @ 0x080D28B4
	push {r4, lr}
	adds r4, r0, #0
	ldrb r0, [r4, #0xd]
	cmp r0, #0
	beq _080D28C4
	cmp r0, #1
	beq _080D28DE
	b _080D28E4
_080D28C4:
	ldr r0, [r4, #0x54]
	ldr r1, [r4, #0x58]
	bl FUN_08009f6c
	str r0, [r4, #0x58]
	movs r1, #0xc2
	lsls r1, r1, #8
	adds r0, r4, #0
	bl SetMotion
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D28DE:
	adds r0, r4, #0
	bl UpdateEntityAnim
_080D28E4:
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0

	thumb_func_start Actor15_Update
Actor15_Update: @ 0x080D28EC
	push {r4, lr}
	adds r4, r0, #0
	ldrb r0, [r4, #0xd]
	cmp r0, #0
	beq _080D28FC
	cmp r0, #1
	beq _080D2922
	b _080D2928
_080D28FC:
	ldr r0, [r4, #0x54]
	ldr r1, [r4, #0x58]
	bl FUN_08009f6c
	ldr r1, _080D2930 @ =0xFFFFE400
	adds r0, r0, r1
	str r0, [r4, #0x58]
	movs r1, #0xca
	lsls r1, r1, #8
	adds r0, r4, #0
	bl SetMotion
	adds r1, r4, #0
	adds r1, #0x25
	movs r0, #0x1f
	strb r0, [r1]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D2922:
	adds r0, r4, #0
	bl UpdateEntityAnim
_080D2928:
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0
_080D2930: .4byte 0xFFFFE400

	thumb_func_start ActorOperator_Update
ActorOperator_Update: @ 0x080D2934
	push {r4, lr}
	adds r4, r0, #0
	ldrb r0, [r4, #0xd]
	cmp r0, #0
	beq _080D2944
	cmp r0, #1
	beq _080D29C4
	b _080D29CA
_080D2944:
	ldr r1, [r4, #0x54]
	ldrb r0, [r4, #0x11]
	cmp r0, #0
	beq _080D2952
	movs r2, #0xc0
	lsls r2, r2, #4
	b _080D2954
_080D2952:
	ldr r2, _080D2994 @ =0xFFFFF400
_080D2954:
	adds r0, r1, r2
	str r0, [r4, #0x54]
	ldr r1, [r4, #0x58]
	bl FUN_08009f6c
	ldr r1, _080D2998 @ =0xFFFFE500
	adds r0, r0, r1
	str r0, [r4, #0x58]
	ldrb r1, [r4, #0x11]
	movs r2, #0xc9
	lsls r2, r2, #8
	adds r0, r2, #0
	orrs r1, r0
	adds r0, r4, #0
	bl SetMotion
	adds r1, r4, #0
	adds r1, #0x25
	movs r0, #0x1f
	strb r0, [r1]
	movs r1, #0
	ldrb r0, [r4, #0x11]
	cmp r0, #0
	bne _080D2986
	movs r1, #1
_080D2986:
	adds r2, r1, #0
	cmp r2, #0
	beq _080D299C
	ldrb r0, [r4, #0xa]
	movs r1, #0x10
	orrs r0, r1
	b _080D29A2
	.align 2, 0
_080D2994: .4byte 0xFFFFF400
_080D2998: .4byte 0xFFFFE500
_080D299C:
	ldrb r1, [r4, #0xa]
	movs r0, #0xef
	ands r0, r1
_080D29A2:
	strb r0, [r4, #0xa]
	adds r1, r2, #0
	adds r0, r4, #0
	adds r0, #0x4c
	strb r1, [r0]
	adds r3, r4, #0
	adds r3, #0x4a
	lsls r1, r1, #4
	ldrb r2, [r3]
	movs r0, #0x11
	rsbs r0, r0, #0
	ands r0, r2
	orrs r0, r1
	strb r0, [r3]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D29C4:
	adds r0, r4, #0
	bl UpdateEntityAnim
_080D29CA:
	pop {r4}
	pop {r0}
	bx r0

	thumb_func_start Actor17_Update
Actor17_Update: @ 0x080D29D0
	push {r4, r5, r6, r7, lr}
	adds r6, r0, #0
	ldrb r7, [r6, #0xd]
	cmp r7, #1
	beq _080D2AC0
	cmp r7, #1
	ble _080D29E0
	b _080D2B34
_080D29E0:
	cmp r7, #0
	beq _080D29E6
	b _080D2B34
_080D29E6:
	ldrb r1, [r6, #0x11]
	movs r0, #0x10
	ands r0, r1
	cmp r0, #0
	beq _080D2A0C
	movs r0, #0x2b
	bl PlaySound
	ldr r0, _080D2AD8 @ =wStaticGraphicTilenums
	movs r2, #0xec
	lsls r2, r2, #1
	adds r0, r0, r2
	movs r1, #0xe0
	lsls r1, r1, #2
	strh r1, [r0]
	ldr r0, _080D2ADC @ =wStaticMotionPalIDs
	adds r0, r0, r2
	movs r1, #8
	strh r1, [r0]
_080D2A0C:
	ldr r4, _080D2AE0 @ =0x00001270
	ldr r1, _080D2AE4 @ =gStaticMotionGraphics
	adds r0, r4, r1
	ldr r1, _080D2AD8 @ =wStaticGraphicTilenums
	movs r5, #0xec
	lsls r5, r5, #1
	adds r1, r1, r5
	ldrh r1, [r1]
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r3, _080D2AE8 @ =gStaticMotionGraphics+12
	adds r4, r4, r3
	ldr r0, _080D2ADC @ =wStaticMotionPalIDs
	adds r0, r0, r5
	ldrh r1, [r0]
	ldrb r0, [r4, #7]
	subs r1, r1, r0
	lsls r1, r1, #5
	movs r0, #0x80
	lsls r0, r0, #2
	adds r1, r1, r0
	adds r0, r4, #0
	bl LoadPalette
	adds r0, r6, #0
	bl InitNonAffineMotion
	ldr r1, _080D2AEC @ =0x0000EC01
	adds r0, r6, #0
	bl SetMotion
	adds r3, r6, #0
	adds r3, #0x45
	ldrb r2, [r3]
	movs r1, #0xd
	rsbs r1, r1, #0
	adds r0, r1, #0
	ands r0, r2
	movs r2, #4
	orrs r0, r2
	strb r0, [r3]
	adds r3, #4
	ldrb r0, [r3]
	ands r1, r0
	orrs r1, r2
	strb r1, [r3]
	ldrb r0, [r6, #0xa]
	orrs r2, r0
	strb r2, [r6, #0xa]
	adds r4, r6, #0
	adds r4, #0x74
	ldrb r1, [r6, #0x11]
	movs r0, #0xf
	ands r0, r1
	lsls r1, r0, #1
	adds r1, r1, r0
	lsls r1, r1, #3
	ldr r0, _080D2AF0 @ =sCollisions_08370B58+(24*2)
	adds r1, r1, r0
	adds r2, r6, #0
	adds r2, #0x54
	adds r0, r4, #0
	movs r3, #9
	bl InitBody
	str r6, [r4, #0x2c]
	str r7, [r4, #0x24]
	ldr r0, [r6, #0x54]
	ldr r1, [r6, #0x58]
	bl FUN_08009f6c
	ldr r1, _080D2AF4 @ =0xFFFFB000
	adds r0, r0, r1
	str r0, [r6, #0x58]
	ldr r1, _080D2AF8 @ =gBlendRegBuffer
	movs r0, #0xfd
	lsls r0, r0, #6
	strh r0, [r1]
	movs r0, #8
	strb r0, [r6, #0x12]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D2AC0:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldrb r0, [r6, #0x12]
	cmp r0, #6
	bls _080D2B00
	ldr r1, _080D2AF8 @ =gBlendRegBuffer
	ldr r0, _080D2AFC @ =0x00001010
	strh r0, [r1, #2]
	adds r2, r1, #0
	b _080D2B16
	.align 2, 0
_080D2AD8: .4byte wStaticGraphicTilenums
_080D2ADC: .4byte wStaticMotionPalIDs
_080D2AE0: .4byte 0x00001270
_080D2AE4: .4byte gStaticMotionGraphics
_080D2AE8: .4byte gStaticMotionGraphics+12
_080D2AEC: .4byte 0x0000EC01
_080D2AF0: .4byte sCollisions_08370B58+(24*2)
_080D2AF4: .4byte 0xFFFFB000
_080D2AF8: .4byte gBlendRegBuffer
_080D2AFC: .4byte 0x00001010
_080D2B00:
	ldr r2, _080D2B3C @ =gBlendRegBuffer
	ldrb r1, [r6, #0x12]
	lsls r0, r1, #1
	adds r0, r0, r1
	movs r1, #0x1f
	ands r0, r1
	movs r3, #0x80
	lsls r3, r3, #5
	adds r1, r3, #0
	orrs r0, r1
	strh r0, [r2, #2]
_080D2B16:
	ldrb r0, [r6, #0x12]
	subs r0, #1
	strb r0, [r6, #0x12]
	lsls r0, r0, #0x18
	lsrs r3, r0, #0x18
	cmp r3, #0
	bne _080D2B34
	ldrb r0, [r6, #0xa]
	movs r1, #0xfe
	ands r1, r0
	strb r1, [r6, #0xa]
	strh r3, [r2]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D2B34:
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0
	.align 2, 0
_080D2B3C: .4byte gBlendRegBuffer

	thumb_func_start Actor18_Update
Actor18_Update: @ 0x080D2B40
	push {r4, lr}
	adds r4, r0, #0
	ldrb r0, [r4, #0xd]
	cmp r0, #0xa
	bls _080D2B4C
	b _080D2D44
_080D2B4C:
	lsls r0, r0, #2
	ldr r1, _080D2B58 @ =_080D2B5C
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D2B58: .4byte _080D2B5C
_080D2B5C: @ jump table
	.4byte _080D2B88 @ case 0
	.4byte _080D2BA4 @ case 1
	.4byte _080D2BBC @ case 2
	.4byte _080D2BE4 @ case 3
	.4byte _080D2C1C @ case 4
	.4byte _080D2C44 @ case 5
	.4byte _080D2C80 @ case 6
	.4byte _080D2CC4 @ case 7
	.4byte _080D2D14 @ case 8
	.4byte _080D2D2E @ case 9
	.4byte _080D2D44 @ case 10
_080D2B88:
	ldr r0, _080D2BB4 @ =wDynamicGraphicTilenums
	movs r2, #0xbe
	lsls r2, r2, #1
	adds r0, r0, r2
	movs r1, #0xf0
	lsls r1, r1, #2
	strh r1, [r0]
	ldr r0, _080D2BB8 @ =wDynamicMotionPalIDs
	adds r0, r0, r2
	movs r1, #9
	strh r1, [r0]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D2BA4:
	movs r1, #0xbe
	lsls r1, r1, #8
	adds r0, r4, #0
	movs r2, #1
	bl FUN_080d0aa0
	b _080D2D38
	.align 2, 0
_080D2BB4: .4byte wDynamicGraphicTilenums
_080D2BB8: .4byte wDynamicMotionPalIDs
_080D2BBC:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldr r0, [r4, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	bne _080D2BD0
	b _080D2D44
_080D2BD0:
	ldr r1, _080D2BE0 @ =0x0000BE01
	adds r0, r4, #0
	bl SetMotion
	movs r0, #8
	strb r0, [r4, #0x12]
	b _080D2D3E
	.align 2, 0
_080D2BE0: .4byte 0x0000BE01
_080D2BE4:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldrb r0, [r4, #0x12]
	subs r0, #1
	strb r0, [r4, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	bne _080D2BFC
	ldr r0, _080D2C14 @ =0x00000101
	bl PlaySound
_080D2BFC:
	adds r0, r4, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	beq _080D2C08
	b _080D2D44
_080D2C08:
	ldr r1, _080D2C18 @ =0x0000BE02
	adds r0, r4, #0
	bl SetMotion
	b _080D2D3E
	.align 2, 0
_080D2C14: .4byte 0x00000101
_080D2C18: .4byte 0x0000BE02
_080D2C1C:
	adds r0, r4, #0
	bl UpdateEntityAnim
	adds r0, r4, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	beq _080D2C2E
	b _080D2D44
_080D2C2E:
	ldr r1, _080D2C40 @ =0x0000BE03
	adds r0, r4, #0
	bl SetMotion
	movs r0, #0x40
	strb r0, [r4, #0x12]
	ldr r0, [r4, #0x58]
	str r0, [r4, #0x68]
	b _080D2D3E
	.align 2, 0
_080D2C40: .4byte 0x0000BE03
_080D2C44:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldr r1, _080D2C7C @ =gSineTable
	ldrb r0, [r4, #0x12]
	lsls r0, r0, #1
	adds r0, r0, r1
	movs r1, #0
	ldrsh r0, [r0, r1]
	ldr r1, [r4, #0x68]
	subs r1, r1, r0
	str r1, [r4, #0x68]
	ldr r2, [r4, #0x58]
	lsls r0, r2, #3
	subs r0, r0, r2
	adds r0, r0, r1
	asrs r1, r0, #3
	str r1, [r4, #0x58]
	ldrb r0, [r4, #0x12]
	subs r0, #1
	strb r0, [r4, #0x12]
	lsls r0, r0, #0x18
	lsrs r0, r0, #0x18
	cmp r0, #0
	bne _080D2D44
	strb r0, [r4, #0x12]
	str r1, [r4, #0x60]
	b _080D2D3E
	.align 2, 0
_080D2C7C: .4byte gSineTable
_080D2C80:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldrb r0, [r4, #0x12]
	adds r0, #1
	strb r0, [r4, #0x12]
	ldr r1, _080D2CC0 @ =gSineTable
	ldrb r0, [r4, #0x12]
	lsls r0, r0, #1
	adds r0, r0, r1
	movs r1, #0
	ldrsh r0, [r0, r1]
	lsls r0, r0, #2
	ldr r1, [r4, #0x60]
	adds r1, r1, r0
	str r1, [r4, #0x68]
	ldr r2, [r4, #0x58]
	lsls r0, r2, #3
	subs r0, r0, r2
	adds r0, r0, r1
	asrs r2, r0, #3
	str r2, [r4, #0x58]
	ldr r0, [r4, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #2
	ands r0, r1
	cmp r0, #0
	beq _080D2D44
	movs r0, #0x40
	strb r0, [r4, #0x12]
	str r2, [r4, #0x68]
	b _080D2D3E
	.align 2, 0
_080D2CC0: .4byte gSineTable
_080D2CC4:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldr r2, [r4, #0x68]
	movs r0, #0x80
	lsls r0, r0, #1
	adds r2, r2, r0
	ldr r1, _080D2D0C @ =gSineTable
	ldrb r0, [r4, #0x12]
	lsls r0, r0, #1
	adds r0, r0, r1
	movs r1, #0
	ldrsh r0, [r0, r1]
	adds r2, r2, r0
	str r2, [r4, #0x68]
	ldr r0, [r4, #0x58]
	lsls r1, r0, #3
	subs r1, r1, r0
	adds r1, r1, r2
	asrs r1, r1, #3
	str r1, [r4, #0x58]
	ldr r0, [r4, #0x54]
	bl PushoutToUp2
	cmp r0, #0
	beq _080D2D44
	ldr r0, [r4, #0x54]
	ldr r1, [r4, #0x58]
	bl FUN_08009f6c
	str r0, [r4, #0x58]
	ldr r1, _080D2D10 @ =0x0000BE0E
	adds r0, r4, #0
	bl SetMotion
	b _080D2D3E
	.align 2, 0
_080D2D0C: .4byte gSineTable
_080D2D10: .4byte 0x0000BE0E
_080D2D14:
	adds r0, r4, #0
	bl UpdateEntityAnim
	adds r0, r4, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	bne _080D2D44
	ldr r0, [r4, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #4
	ands r0, r1
	b _080D2D3A
_080D2D2E:
	ldr r1, _080D2D4C @ =0x0000BE0E
	adds r0, r4, #0
	movs r2, #1
	bl FUN_080d0934
_080D2D38:
	lsls r0, r0, #0x10
_080D2D3A:
	cmp r0, #0
	beq _080D2D44
_080D2D3E:
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D2D44:
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0
_080D2D4C: .4byte 0x0000BE0E

	thumb_func_start Actor19_Update
Actor19_Update: @ 0x080D2D50
	push {r4, lr}
	adds r4, r0, #0
	ldrb r0, [r4, #0xd]
	cmp r0, #1
	beq _080D2DA8
	cmp r0, #1
	bgt _080D2D64
	cmp r0, #0
	beq _080D2D6A
	b _080D2DFE
_080D2D64:
	cmp r0, #2
	beq _080D2DE8
	b _080D2DFE
_080D2D6A:
	ldr r0, _080D2DD4 @ =wDynamicGraphicTilenums
	movs r2, #0xc5
	lsls r2, r2, #1
	adds r0, r0, r2
	movs r1, #0xe0
	lsls r1, r1, #2
	strh r1, [r0]
	ldr r0, _080D2DD8 @ =wDynamicMotionPalIDs
	adds r0, r0, r2
	movs r1, #8
	strh r1, [r0]
	ldr r1, _080D2DDC @ =0x0000C501
	adds r0, r4, #0
	bl SetMotion
	ldr r0, [r4, #0x54]
	str r0, [r4, #0x64]
	movs r1, #0x80
	lsls r1, r1, #5
	adds r0, r0, r1
	str r0, [r4, #0x54]
	ldr r0, [r4, #0x58]
	str r0, [r4, #0x68]
	ldr r0, _080D2DE0 @ =gStageRun+232
	ldr r0, [r0, #0x3c]
	ldr r1, _080D2DE4 @ =0xFFFFB000
	adds r0, r0, r1
	str r0, [r4, #0x58]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D2DA8:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldr r1, [r4, #0x54]
	lsls r0, r1, #7
	subs r0, r0, r1
	ldr r1, [r4, #0x64]
	adds r0, r0, r1
	asrs r0, r0, #7
	str r0, [r4, #0x54]
	ldr r1, [r4, #0x58]
	lsls r0, r1, #7
	subs r0, r0, r1
	ldr r1, [r4, #0x68]
	adds r0, r0, r1
	asrs r0, r0, #7
	str r0, [r4, #0x58]
	ldr r0, [r4, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	b _080D2DF4
	.align 2, 0
_080D2DD4: .4byte wDynamicGraphicTilenums
_080D2DD8: .4byte wDynamicMotionPalIDs
_080D2DDC: .4byte 0x0000C501
_080D2DE0: .4byte gStageRun+232
_080D2DE4: .4byte 0xFFFFB000
_080D2DE8:
	ldr r1, _080D2E04 @ =0x0000C501
	adds r0, r4, #0
	movs r2, #1
	bl FUN_080d0934
	lsls r0, r0, #0x10
_080D2DF4:
	cmp r0, #0
	beq _080D2DFE
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D2DFE:
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0
_080D2E04: .4byte 0x0000C501

	thumb_func_start Actor20_Update
Actor20_Update: @ 0x080D2E08
	push {r4, lr}
	adds r4, r0, #0
	ldrb r0, [r4, #0xd]
	cmp r0, #4
	bhi _080D2E8E
	lsls r0, r0, #2
	ldr r1, _080D2E1C @ =_080D2E20
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D2E1C: .4byte _080D2E20
_080D2E20: @ jump table
	.4byte _080D2E34 @ case 0
	.4byte _080D2E50 @ case 1
	.4byte _080D2E68 @ case 2
	.4byte _080D2E78 @ case 3
	.4byte _080D2E8E @ case 4
_080D2E34:
	ldr r0, _080D2E5C @ =wDynamicGraphicTilenums
	movs r2, #0xb3
	lsls r2, r2, #1
	adds r0, r0, r2
	movs r1, #0xd0
	lsls r1, r1, #2
	strh r1, [r0]
	ldr r0, _080D2E60 @ =wDynamicMotionPalIDs
	adds r0, r0, r2
	movs r1, #7
	strh r1, [r0]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D2E50:
	ldr r1, _080D2E64 @ =0x0000B319
	adds r0, r4, #0
	movs r2, #1
	bl FUN_080d0aa0
	b _080D2E82
	.align 2, 0
_080D2E5C: .4byte wDynamicGraphicTilenums
_080D2E60: .4byte wDynamicMotionPalIDs
_080D2E64: .4byte 0x0000B319
_080D2E68:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldr r0, [r4, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	b _080D2E84
_080D2E78:
	ldr r1, _080D2E94 @ =0x0000B319
	adds r0, r4, #0
	movs r2, #1
	bl FUN_080d0934
_080D2E82:
	lsls r0, r0, #0x10
_080D2E84:
	cmp r0, #0
	beq _080D2E8E
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D2E8E:
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0
_080D2E94: .4byte 0x0000B319

	thumb_func_start initActor21
initActor21: @ 0x080D2E98
	push {r4, lr}
	ldr r2, _080D2ED4 @ =gWindowRegBuffer
	ldrh r3, [r2]
	movs r4, #0x80
	lsls r4, r4, #7
	adds r1, r4, #0
	movs r4, #0
	orrs r1, r3
	strh r1, [r2]
	ldrb r3, [r2, #0xe]
	movs r1, #0xfe
	orrs r1, r3
	strb r1, [r2, #0xe]
	movs r3, #1
	strb r4, [r2, #0xd]
	strb r4, [r0, #0x12]
	ldr r2, _080D2ED8 @ =gSolidFnTable
	ldrb r1, [r0, #9]
	lsls r1, r1, #2
	adds r1, r1, r2
	str r3, [r0, #0xc]
	ldr r1, [r1]
	ldr r1, [r1, #4]
	str r1, [r0, #0x14]
	bl Actor_Update
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0
_080D2ED4: .4byte gWindowRegBuffer
_080D2ED8: .4byte gSolidFnTable

	thumb_func_start Actor21_Update
Actor21_Update: @ 0x080D2EDC
	push {r4, r5, r6, lr}
	adds r6, r0, #0
	ldrb r0, [r6, #0xd]
	cmp r0, #6
	bls _080D2EE8
	b _080D2FEC
_080D2EE8:
	lsls r0, r0, #2
	ldr r1, _080D2EF4 @ =_080D2EF8
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D2EF4: .4byte _080D2EF8
_080D2EF8: @ jump table
	.4byte _080D2F14 @ case 0
	.4byte _080D2F26 @ case 1
	.4byte _080D2F58 @ case 2
	.4byte _080D2F6A @ case 3
	.4byte _080D2F86 @ case 4
	.4byte _080D2FC0 @ case 5
	.4byte _080D2FEC @ case 6
_080D2F14:
	movs r1, #0
	str r1, [r6, #0x54]
	movs r0, #0x93
	lsls r0, r0, #8
	str r0, [r6, #0x58]
	strb r1, [r6, #0x13]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D2F26:
	ldr r2, _080D2F54 @ =gSineTable
	ldrb r1, [r6, #0x13]
	lsls r0, r1, #0x19
	lsrs r0, r0, #0x17
	adds r0, r0, r2
	movs r3, #0
	ldrsh r2, [r0, r3]
	lsls r0, r2, #1
	adds r0, r0, r2
	lsls r0, r0, #4
	str r0, [r6, #0x54]
	adds r1, #1
	strb r1, [r6, #0x13]
	lsls r1, r1, #0x18
	lsrs r1, r1, #0x18
	cmp r1, #0x1f
	bls _080D2FEC
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
	movs r0, #0x10
	strb r0, [r6, #0x13]
	b _080D2FEC
	.align 2, 0
_080D2F54: .4byte gSineTable
_080D2F58:
	ldrb r0, [r6, #0x13]
	subs r0, #1
	strb r0, [r6, #0x13]
	lsls r0, r0, #0x18
	cmp r0, #0
	beq _080D2FEC
	movs r0, #4
	strb r0, [r6, #0x13]
	b _080D2FE6
_080D2F6A:
	ldr r0, [r6, #0x54]
	movs r1, #0x80
	lsls r1, r1, #2
	adds r0, r0, r1
	str r0, [r6, #0x54]
	ldrb r0, [r6, #0x13]
	subs r0, #1
	strb r0, [r6, #0x13]
	lsls r0, r0, #0x18
	cmp r0, #0
	beq _080D2FEC
	movs r0, #8
	strb r0, [r6, #0x13]
	b _080D2FE6
_080D2F86:
	ldrb r1, [r6, #0x13]
	subs r1, #1
	strb r1, [r6, #0x13]
	ldr r2, _080D2FBC @ =gSineTable
	lsls r0, r1, #0x1b
	lsrs r0, r0, #0x17
	adds r0, r0, r2
	movs r3, #0
	ldrsh r2, [r0, r3]
	lsls r0, r2, #1
	adds r0, r0, r2
	lsls r0, r0, #4
	movs r2, #0x80
	lsls r2, r2, #4
	adds r0, r0, r2
	str r0, [r6, #0x54]
	lsls r1, r1, #0x18
	cmp r1, #0
	bne _080D2FEC
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
	movs r0, #0x97
	lsls r0, r0, #1
	bl PlaySound
	b _080D2FEC
	.align 2, 0
_080D2FBC: .4byte gSineTable
_080D2FC0:
	ldr r1, [r6, #0x54]
	lsls r0, r1, #1
	adds r0, r0, r1
	asrs r0, r0, #2
	str r0, [r6, #0x54]
	ldr r1, [r6, #0x58]
	lsls r0, r1, #1
	adds r0, r0, r1
	asrs r0, r0, #2
	str r0, [r6, #0x58]
	movs r1, #0x80
	lsls r1, r1, #3
	cmp r0, r1
	bgt _080D2FEC
	ldr r2, _080D302C @ =gWindowRegBuffer
	ldrh r1, [r2]
	ldr r0, _080D3030 @ =0x0000BFFF
	ands r0, r1
	strh r0, [r2]
_080D2FE6:
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D2FEC:
	ldrb r0, [r6, #0x12]
	adds r0, #1
	strb r0, [r6, #0x12]
	ldr r5, _080D302C @ =gWindowRegBuffer
	ldr r2, [r6, #0x54]
	asrs r2, r2, #8
	movs r3, #1
	ands r3, r0
	lsls r0, r3, #3
	adds r2, r2, r0
	adds r1, r2, #0
	adds r1, #0xbc
	movs r4, #0xff
	ands r1, r4
	movs r0, #0xbc
	subs r0, r0, r2
	lsls r0, r0, #8
	orrs r1, r0
	strh r1, [r5, #6]
	ldr r0, [r6, #0x58]
	asrs r0, r0, #8
	lsls r3, r3, #2
	adds r0, r0, r3
	ands r0, r4
	strh r0, [r5, #0xa]
	ldr r1, _080D3034 @ =gPaletteManager
	ldr r3, _080D3038 @ =0x00007FFF
	adds r0, r3, #0
	strh r0, [r1]
	pop {r4, r5, r6}
	pop {r0}
	bx r0
	.align 2, 0
_080D302C: .4byte gWindowRegBuffer
_080D3030: .4byte 0x0000BFFF
_080D3034: .4byte gPaletteManager
_080D3038: .4byte 0x00007FFF

	thumb_func_start Actor22_Update
Actor22_Update: @ 0x080D303C
	push {r4, r5, r6, lr}
	adds r5, r0, #0
	ldrb r0, [r5, #0xd]
	cmp r0, #4
	bls _080D3048
	b _080D3166
_080D3048:
	lsls r0, r0, #2
	ldr r1, _080D3054 @ =_080D3058
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D3054: .4byte _080D3058
_080D3058: @ jump table
	.4byte _080D306C @ case 0
	.4byte _080D30D6 @ case 1
	.4byte _080D3120 @ case 2
	.4byte _080D3140 @ case 3
	.4byte _080D3166 @ case 4
_080D306C:
	ldr r0, [r5, #0x54]
	ldr r1, [r5, #0x58]
	bl FUN_08009f6c
	str r0, [r5, #0x58]
	movs r4, #0x82
	ldr r0, _080D310C @ =wStaticGraphicTilenums
	lsls r1, r4, #1
	adds r2, r0, r1
	ldr r0, _080D3110 @ =0x0000024D
	strh r0, [r2]
	ldr r0, _080D3114 @ =wStaticMotionPalIDs
	adds r6, r0, r1
	movs r0, #8
	strh r0, [r6]
	ldrb r0, [r5, #0x11]
	cmp r0, #0
	bne _080D30C6
	lsls r4, r4, #2
	adds r4, #0x82
	lsls r4, r4, #2
	ldr r1, _080D3118 @ =gStaticMotionGraphics
	adds r0, r4, r1
	ldrh r1, [r2]
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r0, _080D311C @ =gStaticMotionGraphics+12
	adds r4, r4, r0
	ldrh r1, [r6]
	ldrb r0, [r4, #7]
	subs r1, r1, r0
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #2
	adds r1, r1, r2
	adds r0, r4, #0
	bl LoadPalette
_080D30C6:
	movs r1, #0x82
	lsls r1, r1, #8
	adds r0, r5, #0
	bl SetMotion
	ldrb r0, [r5, #0xd]
	adds r0, #1
	strb r0, [r5, #0xd]
_080D30D6:
	adds r0, r5, #0
	bl UpdateEntityAnim
	ldr r0, [r5, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	beq _080D3166
	movs r2, #0
	ldrb r1, [r5, #0xa]
	movs r0, #0xef
	ands r0, r1
	strb r0, [r5, #0xa]
	adds r0, r5, #0
	adds r0, #0x4c
	strb r2, [r0]
	adds r2, r5, #0
	adds r2, #0x4a
	ldrb r1, [r2]
	movs r0, #0x11
	rsbs r0, r0, #0
	ands r0, r1
	strb r0, [r2]
	movs r0, #8
	strb r0, [r5, #0x12]
	b _080D3160
	.align 2, 0
_080D310C: .4byte wStaticGraphicTilenums
_080D3110: .4byte 0x0000024D
_080D3114: .4byte wStaticMotionPalIDs
_080D3118: .4byte gStaticMotionGraphics
_080D311C: .4byte gStaticMotionGraphics+12
_080D3120:
	adds r0, r5, #0
	bl UpdateEntityAnim
	ldrb r0, [r5, #0x12]
	subs r0, #1
	strb r0, [r5, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	bne _080D3166
	ldr r1, _080D313C @ =0x00008202
	adds r0, r5, #0
	bl SetMotion
	b _080D3160
	.align 2, 0
_080D313C: .4byte 0x00008202
_080D3140:
	adds r0, r5, #0
	bl UpdateEntityAnim
	ldr r1, [r5, #0x54]
	subs r1, #0x80
	str r1, [r5, #0x54]
	ldr r0, _080D316C @ =gStageRun+232
	ldr r0, [r0, #0x38]
	ldr r2, _080D3170 @ =0xFFFF7800
	adds r0, r0, r2
	cmp r1, r0
	bge _080D3166
	ldrb r0, [r5, #0xa]
	movs r1, #0xfe
	ands r1, r0
	strb r1, [r5, #0xa]
_080D3160:
	ldrb r0, [r5, #0xd]
	adds r0, #1
	strb r0, [r5, #0xd]
_080D3166:
	pop {r4, r5, r6}
	pop {r0}
	bx r0
	.align 2, 0
_080D316C: .4byte gStageRun+232
_080D3170: .4byte 0xFFFF7800

	thumb_func_start initActor23
initActor23: @ 0x080D3174
	push {lr}
	ldrb r2, [r0, #0xb]
	movs r1, #8
	movs r3, #0
	orrs r1, r2
	strb r1, [r0, #0xb]
	ldr r1, _080D31A4 @ =Rect_08370c60
	str r1, [r0, #0x30]
	ldr r1, _080D31A8 @ =0x00002001
	strh r1, [r0, #0x26]
	str r3, [r0, #0x5c]
	ldr r2, _080D31AC @ =gSolidFnTable
	ldrb r1, [r0, #9]
	lsls r1, r1, #2
	adds r1, r1, r2
	movs r2, #1
	str r2, [r0, #0xc]
	ldr r1, [r1]
	ldr r1, [r1, #4]
	str r1, [r0, #0x14]
	bl Actor_Update
	pop {r0}
	bx r0
	.align 2, 0
_080D31A4: .4byte Rect_08370c60
_080D31A8: .4byte 0x00002001
_080D31AC: .4byte gSolidFnTable

	thumb_func_start Actor23_Update
Actor23_Update: @ 0x080D31B0
	push {r4, lr}
	adds r4, r0, #0
	ldr r0, [r4, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	beq _080D31EE
	ldr r0, _080D31F4 @ =gStageRun+232
	adds r1, r4, #0
	adds r1, #0x54
	bl Camera_GetDistance
	ldr r1, _080D31F8 @ =0x00000FFF
	cmp r0, r1
	bhi _080D31EE
	ldr r0, [r4, #0x5c]
	adds r0, #4
	str r0, [r4, #0x5c]
	movs r1, #0xe0
	lsls r1, r1, #3
	cmp r0, r1
	ble _080D31E0
	str r1, [r4, #0x5c]
_080D31E0:
	ldr r0, [r4, #0x54]
	ldr r1, [r4, #0x5c]
	adds r0, r0, r1
	str r0, [r4, #0x54]
	ldr r0, [r4, #0x58]
	subs r0, r0, r1
	str r0, [r4, #0x58]
_080D31EE:
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0
_080D31F4: .4byte gStageRun+232
_080D31F8: .4byte 0x00000FFF

	thumb_func_start Actor24_Update
Actor24_Update: @ 0x080D31FC
	push {r4, r5, r6, r7, lr}
	adds r7, r0, #0
	ldrb r0, [r7, #0xd]
	cmp r0, #0
	bne _080D325C
	ldr r6, [r7, #0x28]
	ldr r4, _080D3268 @ =0x0000107C
	ldr r1, _080D326C @ =gStaticMotionGraphics
	adds r0, r4, r1
	ldr r1, _080D3270 @ =wStaticGraphicTilenums
	movs r5, #0xd3
	lsls r5, r5, #1
	adds r1, r1, r5
	ldrh r1, [r1]
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r0, _080D3274 @ =gStaticMotionGraphics+12
	adds r4, r4, r0
	ldr r0, _080D3278 @ =wStaticMotionPalIDs
	adds r0, r0, r5
	ldrh r1, [r0]
	ldrb r0, [r4, #7]
	subs r1, r1, r0
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #2
	adds r1, r1, r2
	adds r0, r4, #0
	bl LoadPalette
	ldr r1, _080D327C @ =0x0000D301
	adds r0, r7, #0
	bl SetMotion
	ldr r0, [r6]
	str r0, [r7, #0x54]
	ldr r0, [r6, #4]
	str r0, [r7, #0x58]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D325C:
	adds r0, r7, #0
	bl UpdateEntityAnim
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0
	.align 2, 0
_080D3268: .4byte 0x0000107C
_080D326C: .4byte gStaticMotionGraphics
_080D3270: .4byte wStaticGraphicTilenums
_080D3274: .4byte gStaticMotionGraphics+12
_080D3278: .4byte wStaticMotionPalIDs
_080D327C: .4byte 0x0000D301

	thumb_func_start Actor25_Update
Actor25_Update: @ 0x080D3280
	push {r4, r5, r6, r7, lr}
	sub sp, #8
	adds r7, r0, #0
	ldrb r0, [r7, #0xd]
	cmp r0, #9
	bls _080D328E
	b _080D358C
_080D328E:
	lsls r0, r0, #2
	ldr r1, _080D3298 @ =_080D329C
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D3298: .4byte _080D329C
_080D329C: @ jump table
	.4byte _080D32C4 @ case 0
	.4byte _080D3352 @ case 1
	.4byte _080D336C @ case 2
	.4byte _080D339C @ case 3
	.4byte _080D33BA @ case 4
	.4byte _080D33DA @ case 5
	.4byte _080D3412 @ case 6
	.4byte _080D3478 @ case 7
	.4byte _080D356C @ case 8
	.4byte _080D3584 @ case 9
_080D32C4:
	ldr r0, [r7, #0x54]
	ldr r1, [r7, #0x58]
	bl FUN_08009f6c
	str r0, [r7, #0x58]
	ldrb r6, [r7, #0x11]
	movs r0, #0xf
	ands r0, r6
	strb r0, [r7, #0x11]
	ldrb r4, [r7, #0x11]
	adds r4, #0xf5
	lsls r5, r4, #2
	adds r5, r5, r4
	lsls r5, r5, #2
	ldr r1, _080D333C @ =gStaticMotionGraphics
	adds r0, r5, r1
	ldr r1, _080D3340 @ =wStaticGraphicTilenums
	lsls r4, r4, #1
	adds r1, r4, r1
	ldrh r1, [r1]
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r3, _080D3344 @ =gStaticMotionGraphics+12
	adds r5, r5, r3
	ldr r0, _080D3348 @ =wStaticMotionPalIDs
	adds r4, r4, r0
	ldrh r1, [r4]
	ldrb r0, [r5, #7]
	subs r1, r1, r0
	lsls r1, r1, #5
	movs r0, #0x80
	lsls r0, r0, #2
	adds r1, r1, r0
	adds r0, r5, #0
	bl LoadPalette
	ldrb r1, [r7, #0x11]
	adds r1, #0xf5
	lsls r1, r1, #0x18
	lsrs r1, r1, #0x10
	adds r0, r7, #0
	bl SetMotion
	cmp r6, #0xf
	bhi _080D334C
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldrb r0, [r7, #0xd]
	adds r0, #2
	strb r0, [r7, #0xd]
	b _080D358C
	.align 2, 0
_080D333C: .4byte gStaticMotionGraphics
_080D3340: .4byte wStaticGraphicTilenums
_080D3344: .4byte gStaticMotionGraphics+12
_080D3348: .4byte wStaticMotionPalIDs
_080D334C:
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D3352:
	ldrb r1, [r7, #0x11]
	adds r1, #0xf5
	lsls r1, r1, #0x18
	lsrs r1, r1, #0x10
	adds r0, r7, #0
	movs r2, #0
	bl FUN_080d0aa0
	lsls r0, r0, #0x10
	cmp r0, #0
	bne _080D336A
	b _080D358C
_080D336A:
	b _080D357C
_080D336C:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r0, [r7, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	bne _080D3380
	b _080D358C
_080D3380:
	adds r0, r7, #0
	bl _GetEntityPaletteID
	adds r1, r0, #0
	lsls r1, r1, #0x18
	lsrs r1, r1, #0x13
	movs r2, #0x80
	lsls r2, r2, #2
	adds r0, r2, #0
	orrs r1, r0
	movs r0, #0xf8
	bl StartPaletteAnimation
	b _080D357C
_080D339C:
	adds r0, r7, #0
	bl UpdateEntityAnim
	movs r0, #0xf8
	bl StepPaletteAnimation
	lsls r0, r0, #0x18
	lsrs r0, r0, #0x18
	cmp r0, #3
	beq _080D33B2
	b _080D358C
_080D33B2:
	movs r0, #0xf8
	bl RemovePaletteAnimation
	b _080D357C
_080D33BA:
	adds r0, r7, #0
	bl _GetEntityPaletteID
	adds r1, r0, #0
	lsls r1, r1, #0x18
	lsrs r1, r1, #0x13
	movs r3, #0x80
	lsls r3, r3, #2
	adds r0, r3, #0
	orrs r1, r0
	movs r0, #0xf9
	bl StartPaletteAnimation
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D33DA:
	adds r0, r7, #0
	bl UpdateEntityAnim
	movs r0, #0xf9
	bl StepPaletteAnimation
	lsls r0, r0, #0x18
	lsrs r0, r0, #0x18
	cmp r0, #4
	beq _080D33F0
	b _080D358C
_080D33F0:
	movs r0, #0xf9
	bl RemovePaletteAnimation
	adds r0, r7, #0
	bl _GetEntityPaletteID
	adds r1, r0, #0
	lsls r1, r1, #0x18
	lsrs r1, r1, #0x13
	movs r2, #0x80
	lsls r2, r2, #2
	adds r0, r2, #0
	orrs r1, r0
	movs r0, #0xfa
	bl StartPaletteAnimation
	b _080D357C
_080D3412:
	adds r0, r7, #0
	bl UpdateEntityAnim
	movs r0, #0xfa
	bl StepPaletteAnimation
	lsls r0, r0, #0x18
	lsrs r0, r0, #0x18
	cmp r0, #3
	beq _080D3428
	b _080D358C
_080D3428:
	ldr r0, [r7, #0x54]
	str r0, [r7, #0x64]
	ldr r5, _080D34A0 @ =s32_ARRAY_08370de8
	ldrb r0, [r7, #0x11]
	lsls r0, r0, #2
	adds r0, r0, r5
	ldr r1, [r0]
	lsls r1, r1, #7
	ldr r0, [r7, #0x58]
	subs r0, r0, r1
	str r0, [r7, #0x68]
	adds r0, r7, #0
	adds r0, #0x64
	movs r1, #1
	movs r2, #0
	bl CreateVFX39
	str r0, [r7, #0x28]
	adds r0, #0x74
	movs r4, #0
	movs r1, #0x1f
	strb r1, [r0]
	ldr r0, [r7, #0x28]
	adds r0, #0x75
	strb r1, [r0]
	ldr r0, [r7, #0x28]
	adds r0, #0x76
	strb r1, [r0]
	movs r0, #0x58
	bl PlaySound
	strb r4, [r7, #0x12]
	ldrb r0, [r7, #0x11]
	lsls r0, r0, #2
	adds r0, r0, r5
	ldr r0, [r0]
	str r0, [r7, #0x5c]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D3478:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldrb r0, [r7, #0x12]
	adds r3, r0, #1
	strb r3, [r7, #0x12]
	lsls r0, r3, #0x18
	lsrs r0, r0, #0x18
	cmp r0, #0x1f
	bhi _080D34A8
	ldr r2, [r7, #0x28]
	ldr r1, _080D34A4 @ =gSineTable
	lsls r0, r3, #0x19
	lsrs r0, r0, #0x17
	adds r0, r0, r1
	movs r3, #0
	ldrsh r1, [r0, r3]
	ldr r0, [r7, #0x5c]
	b _080D34EA
	.align 2, 0
_080D34A0: .4byte s32_ARRAY_08370de8
_080D34A4: .4byte gSineTable
_080D34A8:
	cmp r0, #0x20
	bne _080D34C0
	ldr r1, [r7, #0x28]
	ldr r0, [r7, #0x5c]
	subs r0, #2
	lsls r0, r0, #8
	str r0, [r1, #0x78]
	ldrb r1, [r7, #0xa]
	movs r0, #0xfe
	ands r0, r1
	strb r0, [r7, #0xa]
	b _080D3556
_080D34C0:
	cmp r0, #0x35
	bhi _080D34D0
	ldr r1, [r7, #0x28]
	ldr r0, [r7, #0x5c]
	subs r0, #4
	lsls r0, r0, #8
	str r0, [r1, #0x78]
	b _080D3556
_080D34D0:
	cmp r0, #0x3f
	bhi _080D34F4
	ldr r2, [r7, #0x28]
	ldr r1, _080D34F0 @ =gSineTable
	movs r0, #0x40
	subs r0, r0, r3
	lsls r0, r0, #0x1b
	lsrs r0, r0, #0x17
	adds r0, r0, r1
	movs r3, #0
	ldrsh r1, [r0, r3]
	ldr r0, [r7, #0x5c]
	subs r0, #4
_080D34EA:
	muls r0, r1, r0
	str r0, [r2, #0x78]
	b _080D3556
	.align 2, 0
_080D34F0: .4byte gSineTable
_080D34F4:
	movs r4, #0
	ldr r5, _080D3568 @ =s32_ARRAY_08370de8
_080D34F8:
	lsls r1, r4, #0x18
	lsrs r1, r1, #0x18
	ldr r2, [r7, #0x54]
	ldr r3, [r7, #0x58]
	ldrb r0, [r7, #0x11]
	lsls r0, r0, #2
	adds r0, r0, r5
	ldr r0, [r0]
	str r0, [sp]
	movs r0, #0
	str r0, [sp, #4]
	movs r0, #2
	bl FUN_080c5684
	lsls r0, r4, #0x10
	movs r1, #0x80
	lsls r1, r1, #0xc
	adds r0, r0, r1
	lsrs r4, r0, #0x10
	asrs r0, r0, #0x10
	cmp r0, #0xff
	ble _080D34F8
	ldr r0, [r7, #0x28]
	adds r0, #0x77
	movs r1, #1
	strb r1, [r0]
	movs r0, #0xfa
	bl RemovePaletteAnimation
	ldrb r4, [r7, #0x11]
	adds r4, #0xfb
	adds r0, r7, #0
	bl _GetEntityPaletteID
	adds r1, r0, #0
	lsls r1, r1, #0x18
	lsrs r1, r1, #0x13
	movs r2, #0x80
	lsls r2, r2, #2
	adds r0, r2, #0
	orrs r1, r0
	adds r0, r4, #0
	bl StartPaletteAnimation
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D3556:
	ldr r2, [r7, #0x28]
	ldrb r0, [r7, #0x12]
	movs r1, #1
	ands r1, r0
	lsls r1, r1, #0xb
	ldr r0, [r2, #0x78]
	adds r0, r0, r1
	str r0, [r2, #0x78]
	b _080D358C
	.align 2, 0
_080D3568: .4byte s32_ARRAY_08370de8
_080D356C:
	ldrb r0, [r7, #0x11]
	adds r0, #0xfb
	bl StepPaletteAnimation
	lsls r0, r0, #0x18
	lsrs r0, r0, #0x18
	cmp r0, #3
	bne _080D358C
_080D357C:
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
	b _080D358C
_080D3584:
	ldrb r0, [r7, #0x11]
	adds r0, #0xfb
	bl RemovePaletteAnimation
_080D358C:
	add sp, #8
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0

	thumb_func_start Actor26_Update
Actor26_Update: @ 0x080D3594
	push {r4, r5, r6, r7, lr}
	adds r7, r0, #0
	ldrb r0, [r7, #0xd]
	cmp r0, #1
	beq _080D360C
	cmp r0, #1
	bgt _080D368C
	cmp r0, #0
	bne _080D368C
	ldr r1, _080D3694 @ =wStaticGraphicTilenums
	adds r1, #0xa2
	ldrh r0, [r1]
	str r0, [r7, #0x64]
	ldr r5, _080D3698 @ =wStaticMotionPalIDs
	adds r5, #0xa2
	ldrh r0, [r5]
	str r0, [r7, #0x68]
	ldr r0, [r7, #0x54]
	str r0, [r7, #0x5c]
	ldr r0, [r7, #0x58]
	str r0, [r7, #0x60]
	movs r6, #0
	ldr r0, _080D369C @ =0x00000305
	strh r0, [r1]
	movs r0, #8
	strh r0, [r5]
	ldr r4, _080D36A0 @ =0x00000654
	ldr r2, _080D36A4 @ =gStaticMotionGraphics
	adds r0, r4, r2
	ldrh r1, [r1]
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r0, _080D36A8 @ =gStaticMotionGraphics+12
	adds r4, r4, r0
	ldrh r1, [r5]
	ldrb r0, [r4, #7]
	subs r1, r1, r0
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #2
	adds r1, r1, r2
	adds r0, r4, #0
	bl LoadPalette
	movs r1, #0xa2
	lsls r1, r1, #7
	adds r0, r7, #0
	bl SetMotion
	strb r6, [r7, #0x12]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D360C:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldrb r1, [r7, #0x12]
	movs r0, #0xf
	ands r0, r1
	cmp r0, #0
	bne _080D3628
	ldr r2, [r7, #0x54]
	ldr r3, [r7, #0x58]
	movs r0, #3
	movs r1, #0
	bl FUN_080c5628
_080D3628:
	ldrb r1, [r7, #0x12]
	adds r1, #1
	strb r1, [r7, #0x12]
	ldr r2, [r7, #0x5c]
	movs r4, #0x80
	lsls r4, r4, #2
	adds r2, r2, r4
	str r2, [r7, #0x5c]
	ldr r3, _080D36AC @ =gSineTable
	lsls r0, r1, #0x19
	movs r4, #0x80
	lsls r4, r4, #0x17
	adds r0, r0, r4
	lsrs r0, r0, #0x17
	adds r0, r0, r3
	movs r4, #0
	ldrsh r0, [r0, r4]
	lsls r0, r0, #1
	adds r2, r2, r0
	str r2, [r7, #0x54]
	lsls r1, r1, #0x1a
	lsrs r1, r1, #0x17
	adds r1, r1, r3
	movs r0, #0
	ldrsh r1, [r1, r0]
	lsls r1, r1, #2
	ldr r0, [r7, #0x60]
	adds r0, r0, r1
	str r0, [r7, #0x58]
	ldr r0, _080D36B0 @ =gStageRun+232
	ldr r0, [r0, #0x38]
	ldr r1, _080D36B4 @ =0x000097FF
	adds r0, r0, r1
	cmp r2, r0
	blt _080D368C
	ldrb r1, [r7, #0xa]
	movs r0, #0xfe
	ands r0, r1
	strb r0, [r7, #0xa]
	ldr r0, _080D3694 @ =wStaticGraphicTilenums
	adds r0, #0xa2
	ldr r1, [r7, #0x64]
	strh r1, [r0]
	ldr r0, _080D3698 @ =wStaticMotionPalIDs
	adds r0, #0xa2
	ldr r1, [r7, #0x68]
	strh r1, [r0]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D368C:
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0
	.align 2, 0
_080D3694: .4byte wStaticGraphicTilenums
_080D3698: .4byte wStaticMotionPalIDs
_080D369C: .4byte 0x00000305
_080D36A0: .4byte 0x00000654
_080D36A4: .4byte gStaticMotionGraphics
_080D36A8: .4byte gStaticMotionGraphics+12
_080D36AC: .4byte gSineTable
_080D36B0: .4byte gStageRun+232
_080D36B4: .4byte 0x000097FF

	thumb_func_start Actor27_Update
Actor27_Update: @ 0x080D36B8
	push {r4, lr}
	adds r4, r0, #0
	ldrb r0, [r4, #0xd]
	cmp r0, #9
	bls _080D36C4
	b _080D3890
_080D36C4:
	lsls r0, r0, #2
	ldr r1, _080D36D0 @ =_080D36D4
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D36D0: .4byte _080D36D4
_080D36D4: @ jump table
	.4byte _080D36FC @ case 0
	.4byte _080D3732 @ case 1
	.4byte _080D374C @ case 2
	.4byte _080D3760 @ case 3
	.4byte _080D378E @ case 4
	.4byte _080D37B4 @ case 5
	.4byte _080D37C6 @ case 6
	.4byte _080D37FA @ case 7
	.4byte _080D3828 @ case 8
	.4byte _080D3890 @ case 9
_080D36FC:
	ldr r0, [r4, #0x54]
	ldr r1, [r4, #0x58]
	bl FUN_08009f6c
	str r0, [r4, #0x58]
	ldr r2, _080D3740 @ =wDynamicGraphicTilenums
	movs r3, #0xa4
	lsls r3, r3, #1
	adds r2, r2, r3
	ldrh r0, [r2]
	str r0, [r4, #0x64]
	ldr r1, _080D3744 @ =wDynamicMotionPalIDs
	adds r1, r1, r3
	ldrh r0, [r1]
	str r0, [r4, #0x68]
	ldr r0, _080D3748 @ =0x00000305
	strh r0, [r2]
	movs r0, #9
	strh r0, [r1]
	movs r1, #0xa4
	lsls r1, r1, #8
	adds r0, r4, #0
	bl SetMotion
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D3732:
	ldr r0, [r4, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	beq _080D37A8
	b _080D379A
	.align 2, 0
_080D3740: .4byte wDynamicGraphicTilenums
_080D3744: .4byte wDynamicMotionPalIDs
_080D3748: .4byte 0x00000305
_080D374C:
	adds r0, r4, #0
	bl UpdateEntityAnim
	adds r0, r4, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	beq _080D375E
	b _080D3890
_080D375E:
	b _080D388A
_080D3760:
	movs r1, #0xa4
	lsls r1, r1, #8
	adds r0, r4, #0
	bl SetMotion
	movs r2, #0
	ldrb r1, [r4, #0xa]
	movs r0, #0xef
	ands r0, r1
	strb r0, [r4, #0xa]
	adds r0, r4, #0
	adds r0, #0x4c
	strb r2, [r0]
	adds r2, r4, #0
	adds r2, #0x4a
	ldrb r1, [r2]
	movs r0, #0x11
	rsbs r0, r0, #0
	ands r0, r1
	strb r0, [r2]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D378E:
	ldr r0, [r4, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	bne _080D37A8
_080D379A:
	ldr r1, _080D37B0 @ =0x0000A408
	adds r0, r4, #0
	bl SetMotion
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D37A8:
	adds r0, r4, #0
	bl UpdateEntityAnim
	b _080D3890
	.align 2, 0
_080D37B0: .4byte 0x0000A408
_080D37B4:
	adds r0, r4, #0
	bl UpdateEntityAnim
	adds r0, r4, #0
	adds r0, #0x73
	ldrb r0, [r0]
	cmp r0, #3
	bne _080D3890
	b _080D388A
_080D37C6:
	movs r1, #0xa4
	lsls r1, r1, #8
	adds r0, r4, #0
	bl SetMotion
	movs r2, #1
	ldrb r1, [r4, #0xa]
	movs r0, #0x10
	orrs r0, r1
	strb r0, [r4, #0xa]
	adds r0, r4, #0
	adds r0, #0x4c
	strb r2, [r0]
	adds r3, r4, #0
	adds r3, #0x4a
	movs r2, #0x10
	ldrb r1, [r3]
	movs r0, #0x11
	rsbs r0, r0, #0
	ands r0, r1
	orrs r0, r2
	strb r0, [r3]
	strb r2, [r4, #0x12]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D37FA:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldrb r0, [r4, #0x12]
	subs r0, #1
	strb r0, [r4, #0x12]
	lsls r0, r0, #0x18
	cmp r0, #0
	bne _080D3890
	ldr r1, _080D3820 @ =0x0000A405
	adds r0, r4, #0
	bl SetMotion
	ldr r0, _080D3824 @ =0xFFFFFB00
	str r0, [r4, #0x60]
	ldr r0, [r4, #0x58]
	str r0, [r4, #0x5c]
	b _080D388A
	.align 2, 0
_080D3820: .4byte 0x0000A405
_080D3824: .4byte 0xFFFFFB00
_080D3828:
	ldr r0, [r4, #0x54]
	movs r1, #0xb8
	lsls r1, r1, #1
	adds r0, r0, r1
	str r0, [r4, #0x54]
	ldr r0, [r4, #0x58]
	ldr r1, [r4, #0x60]
	adds r0, r0, r1
	str r0, [r4, #0x58]
	adds r1, #0x40
	str r1, [r4, #0x60]
	cmp r1, #0
	ble _080D385A
	ldrb r0, [r4, #0x1e]
	lsls r0, r0, #8
	adds r1, r4, #0
	adds r1, #0x70
	ldrb r1, [r1]
	orrs r0, r1
	ldr r1, _080D3898 @ =0x0000A406
	cmp r0, r1
	beq _080D385A
	adds r0, r4, #0
	bl SetMotion
_080D385A:
	adds r0, r4, #0
	bl UpdateEntityAnim
	ldr r0, [r4, #0x5c]
	movs r1, #0xd0
	lsls r1, r1, #6
	adds r0, r0, r1
	ldr r1, [r4, #0x58]
	cmp r0, r1
	bge _080D3890
	ldr r0, _080D389C @ =wDynamicGraphicTilenums
	movs r2, #0xa4
	lsls r2, r2, #1
	adds r0, r0, r2
	ldr r1, [r4, #0x64]
	strh r1, [r0]
	ldr r0, _080D38A0 @ =wDynamicMotionPalIDs
	adds r0, r0, r2
	ldr r1, [r4, #0x68]
	strh r1, [r0]
	ldrb r1, [r4, #0xa]
	movs r0, #0xfe
	ands r0, r1
	strb r0, [r4, #0xa]
_080D388A:
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D3890:
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0
_080D3898: .4byte 0x0000A406
_080D389C: .4byte wDynamicGraphicTilenums
_080D38A0: .4byte wDynamicMotionPalIDs

	thumb_func_start initActor28
initActor28: @ 0x080D38A4
	push {r4, lr}
	ldr r2, _080D38E0 @ =gWindowRegBuffer
	ldrh r3, [r2]
	movs r4, #0x80
	lsls r4, r4, #7
	adds r1, r4, #0
	movs r4, #0
	orrs r1, r3
	strh r1, [r2]
	strb r4, [r2, #0xd]
	ldrb r3, [r2, #0xe]
	movs r1, #0xfe
	orrs r1, r3
	strb r1, [r2, #0xe]
	strb r4, [r0, #0x12]
	ldr r2, _080D38E4 @ =gSolidFnTable
	ldrb r1, [r0, #9]
	lsls r1, r1, #2
	adds r1, r1, r2
	movs r2, #1
	str r2, [r0, #0xc]
	ldr r1, [r1]
	ldr r1, [r1, #4]
	str r1, [r0, #0x14]
	bl Actor_Update
	pop {r4}
	pop {r0}
	bx r0
	.align 2, 0
_080D38E0: .4byte gWindowRegBuffer
_080D38E4: .4byte gSolidFnTable

	thumb_func_start Actor28_Update
Actor28_Update: @ 0x080D38E8
	push {r4, r5, r6, lr}
	adds r6, r0, #0
	ldrb r0, [r6, #0xd]
	cmp r0, #4
	bhi _080D39A6
	lsls r0, r0, #2
	ldr r1, _080D38FC @ =_080D3900
	adds r0, r0, r1
	ldr r0, [r0]
	mov pc, r0
	.align 2, 0
_080D38FC: .4byte _080D3900
_080D3900: @ jump table
	.4byte _080D3914 @ case 0
	.4byte _080D392E @ case 1
	.4byte _080D3960 @ case 2
	.4byte _080D3976 @ case 3
	.4byte _080D39A6 @ case 4
_080D3914:
	movs r4, #0
	str r4, [r6, #0x54]
	movs r0, #0x93
	lsls r0, r0, #8
	str r0, [r6, #0x58]
	movs r0, #0x97
	lsls r0, r0, #1
	bl PlaySound
	strb r4, [r6, #0x13]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D392E:
	ldr r2, _080D395C @ =gSineTable
	ldrb r1, [r6, #0x13]
	lsls r0, r1, #0x1a
	lsrs r0, r0, #0x17
	adds r0, r0, r2
	movs r3, #0
	ldrsh r2, [r0, r3]
	lsls r0, r2, #1
	adds r0, r0, r2
	lsls r0, r0, #4
	str r0, [r6, #0x54]
	adds r1, #1
	strb r1, [r6, #0x13]
	lsls r1, r1, #0x18
	lsrs r1, r1, #0x18
	cmp r1, #0xf
	bls _080D39A6
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
	movs r0, #0x20
	strb r0, [r6, #0x13]
	b _080D39A6
	.align 2, 0
_080D395C: .4byte gSineTable
_080D3960:
	ldrb r0, [r6, #0x13]
	subs r0, #1
	strb r0, [r6, #0x13]
	lsls r0, r0, #0x18
	cmp r0, #0
	bne _080D39A6
	movs r0, #0x20
	strb r0, [r6, #0x13]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D3976:
	ldr r2, _080D39E8 @ =gSineTable
	ldrb r1, [r6, #0x13]
	lsls r0, r1, #0x19
	lsrs r0, r0, #0x17
	adds r0, r0, r2
	movs r3, #0
	ldrsh r2, [r0, r3]
	lsls r0, r2, #1
	adds r0, r0, r2
	lsls r0, r0, #4
	str r0, [r6, #0x54]
	subs r1, #1
	strb r1, [r6, #0x13]
	lsls r1, r1, #0x18
	cmp r1, #0
	bne _080D39A6
	ldr r2, _080D39EC @ =gWindowRegBuffer
	ldrh r1, [r2]
	ldr r0, _080D39F0 @ =0x0000BFFF
	ands r0, r1
	strh r0, [r2]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D39A6:
	ldrb r0, [r6, #0x12]
	adds r0, #1
	strb r0, [r6, #0x12]
	ldr r5, _080D39EC @ =gWindowRegBuffer
	ldr r2, [r6, #0x54]
	asrs r2, r2, #8
	movs r3, #1
	ands r3, r0
	lsls r0, r3, #3
	adds r2, r2, r0
	adds r1, r2, #0
	adds r1, #0xbc
	movs r4, #0xff
	ands r1, r4
	movs r0, #0xbc
	subs r0, r0, r2
	lsls r0, r0, #8
	orrs r1, r0
	strh r1, [r5, #6]
	ldr r0, [r6, #0x58]
	asrs r0, r0, #8
	lsls r3, r3, #2
	adds r0, r0, r3
	ands r0, r4
	strh r0, [r5, #0xa]
	ldr r1, _080D39F4 @ =gPaletteManager
	ldr r2, _080D39F8 @ =0x00007FFF
	adds r0, r2, #0
	strh r0, [r1]
	pop {r4, r5, r6}
	pop {r0}
	bx r0
	.align 2, 0
_080D39E8: .4byte gSineTable
_080D39EC: .4byte gWindowRegBuffer
_080D39F0: .4byte 0x0000BFFF
_080D39F4: .4byte gPaletteManager
_080D39F8: .4byte 0x00007FFF

	thumb_func_start Actor29_Update
Actor29_Update: @ 0x080D39FC
	push {r4, r5, r6, r7, lr}
	sub sp, #8
	adds r6, r0, #0
	ldrb r7, [r6, #0xd]
	cmp r7, #1
	beq _080D3A7E
	cmp r7, #1
	bgt _080D3A12
	cmp r7, #0
	beq _080D3A1A
	b _080D3B2E
_080D3A12:
	cmp r7, #2
	bne _080D3A18
	b _080D3B24
_080D3A18:
	b _080D3B2E
_080D3A1A:
	ldr r0, [r6, #0x54]
	ldr r1, _080D3AF8 @ =0xFFFF1000
	adds r0, r0, r1
	ldr r1, [r6, #0x58]
	bl FUN_08009f6c
	adds r0, #1
	str r0, [r6, #0x58]
	ldr r0, _080D3AFC @ =wStaticGraphicTilenums
	movs r5, #0
	ldr r1, _080D3B00 @ =0x000003CE
	strh r1, [r0, #2]
	ldr r4, _080D3B04 @ =wStaticMotionPalIDs
	movs r0, #9
	strh r0, [r4, #2]
	ldr r0, _080D3B08 @ =0x085D790C
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r0, _080D3B0C @ =0x085D7918
	ldrh r1, [r4, #2]
	ldrb r2, [r0, #7]
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #2
	adds r1, r1, r2
	bl LoadPalette
	movs r1, #0x80
	lsls r1, r1, #1
	adds r0, r6, #0
	bl SetMotion
	adds r1, r6, #0
	adds r1, #0x54
	movs r0, #8
	bl AppendQuake
	strb r5, [r6, #0x12]
	str r7, [r6, #0x60]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
_080D3A7E:
	adds r0, r6, #0
	bl UpdateEntityAnim
	ldr r1, [r6, #0x60]
	adds r1, #0x10
	str r1, [r6, #0x60]
	ldr r0, [r6, #0x58]
	adds r0, r0, r1
	str r0, [r6, #0x58]
	adds r4, r6, #0
	adds r4, #0x54
	movs r0, #2
	adds r1, r4, #0
	bl AppendQuake
	ldrb r0, [r6, #0x12]
	adds r0, #1
	strb r0, [r6, #0x12]
	movs r1, #3
	ands r0, r1
	cmp r0, #0
	beq _080D3AD6
	ldr r0, [r6, #0x54]
	ldr r1, _080D3B10 @ =0xFFFFC000
	adds r0, r0, r1
	str r0, [sp]
	ldr r2, _080D3B14 @ =RNG_0202f388
	ldr r1, [r2]
	ldr r0, _080D3B18 @ =0x000343FD
	muls r0, r1, r0
	ldr r1, _080D3B1C @ =0x00269EC3
	adds r0, r0, r1
	lsls r0, r0, #1
	lsrs r1, r0, #1
	str r1, [r2]
	lsls r0, r0, #3
	lsrs r0, r0, #0x14
	ldr r1, [r6, #0x58]
	adds r1, r1, r0
	str r1, [sp, #4]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
_080D3AD6:
	ldr r0, _080D3B20 @ =gStageRun+232
	adds r1, r4, #0
	bl Camera_GetDistance
	movs r1, #0x80
	lsls r1, r1, #4
	cmp r0, r1
	bls _080D3B2E
	ldrb r0, [r6, #0xa]
	movs r1, #0xfe
	ands r1, r0
	strb r1, [r6, #0xa]
	ldrb r0, [r6, #0xd]
	adds r0, #1
	strb r0, [r6, #0xd]
	b _080D3B2E
	.align 2, 0
_080D3AF8: .4byte 0xFFFF1000
_080D3AFC: .4byte wStaticGraphicTilenums
_080D3B00: .4byte 0x000003CE
_080D3B04: .4byte wStaticMotionPalIDs
_080D3B08: .4byte gStaticMotionGraphics+(20*1)
_080D3B0C: .4byte gStaticMotionGraphics+(20*1)+12
_080D3B10: .4byte 0xFFFFC000
_080D3B14: .4byte RNG_0202f388
_080D3B18: .4byte 0x000343FD
_080D3B1C: .4byte 0x00269EC3
_080D3B20: .4byte gStageRun+232
_080D3B24:
	adds r1, r6, #0
	adds r1, #0x54
	movs r0, #2
	bl AppendQuake
_080D3B2E:
	add sp, #8
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0
	.align 2, 0

	thumb_func_start Actor30_Update
Actor30_Update: @ 0x080D3B38
	push {r4, r5, r6, r7, lr}
	mov r7, sl
	mov r6, sb
	mov r5, r8
	push {r5, r6, r7}
	sub sp, #8
	adds r7, r0, #0
	ldrb r0, [r7, #0xd]
	cmp r0, #1
	beq _080D3C16
	cmp r0, #1
	bgt _080D3B56
	cmp r0, #0
	beq _080D3B64
	b _080D3D10
_080D3B56:
	cmp r0, #2
	bne _080D3B5C
	b _080D3C8C
_080D3B5C:
	cmp r0, #3
	bne _080D3B62
	b _080D3D08
_080D3B62:
	b _080D3D10
_080D3B64:
	ldr r0, [r7, #0x54]
	ldr r1, _080D3CD4 @ =0xFFFF6000
	adds r0, r0, r1
	ldr r1, [r7, #0x58]
	bl FUN_08009f6c
	ldr r2, _080D3CD8 @ =0x00000101
	adds r0, r0, r2
	str r0, [r7, #0x58]
	ldr r1, _080D3CDC @ =wStaticGraphicTilenums
	ldr r0, _080D3CE0 @ =0x000003CE
	strh r0, [r1, #2]
	ldr r6, _080D3CE4 @ =wStaticMotionPalIDs
	movs r0, #9
	strh r0, [r6, #2]
	movs r4, #0xb9
	lsls r0, r4, #1
	mov r8, r0
	adds r2, r1, #0
	add r2, r8
	mov sl, r2
	ldr r0, _080D3CE8 @ =0x000003AF
	strh r0, [r2]
	add r8, r6
	movs r0, #0xa
	mov r2, r8
	strh r0, [r2]
	ldr r5, _080D3CEC @ =gStaticMotionGraphics
	adds r0, r5, #0
	adds r0, #0x14
	ldrh r1, [r1, #2]
	ldrh r2, [r0, #6]
	lsrs r2, r2, #6
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r2, #0x80
	lsls r2, r2, #9
	adds r1, r1, r2
	bl LoadGraphic
	ldr r0, _080D3CF0 @ =gStaticMotionGraphics+12
	mov sb, r0
	adds r0, #0x14
	ldrh r1, [r6, #2]
	ldrb r2, [r0, #7]
	subs r1, r1, r2
	lsls r1, r1, #5
	movs r6, #0x80
	lsls r6, r6, #2
	adds r1, r1, r6
	bl LoadPalette
	lsls r4, r4, #4
	movs r1, #0xb9
	lsls r1, r1, #2
	adds r4, r4, r1
	adds r5, r4, r5
	mov r2, sl
	ldrh r1, [r2]
	ldrh r0, [r5, #6]
	lsrs r0, r0, #6
	subs r1, r1, r0
	lsls r1, r1, #5
	movs r0, #0x80
	lsls r0, r0, #9
	adds r1, r1, r0
	adds r0, r5, #0
	bl LoadGraphic
	add r4, sb
	mov r2, r8
	ldrh r1, [r2]
	ldrb r0, [r4, #7]
	subs r1, r1, r0
	lsls r1, r1, #5
	adds r1, r1, r6
	adds r0, r4, #0
	bl LoadPalette
	movs r1, #0x80
	lsls r1, r1, #1
	adds r0, r7, #0
	bl SetMotion
	movs r0, #0
	strb r0, [r7, #0x12]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D3C16:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r0, [r7, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #1
	ands r0, r1
	cmp r0, #0
	beq _080D3D10
	adds r1, r7, #0
	adds r1, #0x54
	movs r0, #0x10
	bl AppendQuake
	ldr r5, _080D3CF4 @ =RNG_0202f388
	mov r6, sp
	movs r4, #3
_080D3C38:
	ldr r0, [r7, #0x54]
	ldr r1, _080D3CF8 @ =0xFFFFC000
	adds r0, r0, r1
	str r0, [sp]
	ldr r1, [r5]
	ldr r0, _080D3CFC @ =0x000343FD
	muls r1, r0, r1
	ldr r2, _080D3D00 @ =0x00269EC3
	adds r1, r1, r2
	lsls r1, r1, #1
	lsrs r0, r1, #1
	str r0, [r5]
	lsls r1, r1, #3
	lsrs r1, r1, #0x14
	ldr r0, [r7, #0x58]
	adds r0, r0, r1
	str r0, [r6, #4]
	movs r0, #3
	mov r1, sp
	bl CreateSmoke
	subs r4, #1
	cmp r4, #0
	bge _080D3C38
	ldr r0, _080D3D04 @ =pZero2
	ldr r0, [r0]
	ldr r0, [r0, #0x58]
	str r0, [r7, #0x64]
	adds r0, r7, #0
	bl InitRotatableMotion
	movs r1, #0x80
	lsls r1, r1, #1
	adds r0, r7, #0
	bl SetMotion
	movs r0, #0
	str r0, [r7, #0x60]
	str r0, [r7, #0x68]
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
_080D3C8C:
	adds r0, r7, #0
	bl UpdateEntityAnim
	ldr r1, [r7, #0x60]
	adds r1, #1
	str r1, [r7, #0x60]
	ldr r0, [r7, #0x68]
	adds r0, r0, r1
	str r0, [r7, #0x68]
	asrs r0, r0, #0xb
	adds r1, r7, #0
	adds r1, #0x24
	strb r0, [r1]
	ldr r1, [r7, #0x60]
	asrs r2, r1, #2
	ldr r0, [r7, #0x58]
	subs r0, r0, r2
	str r0, [r7, #0x58]
	asrs r1, r1, #1
	ldr r0, [r7, #0x64]
	subs r0, r0, r1
	str r0, [r7, #0x64]
	ldr r1, _080D3D04 @ =pZero2
	ldr r1, [r1]
	str r0, [r1, #0x58]
	ldr r0, [r7, #0x18]
	ldrb r1, [r0, #9]
	movs r0, #2
	ands r0, r1
	cmp r0, #0
	beq _080D3D10
	ldrb r0, [r7, #0xd]
	adds r0, #1
	strb r0, [r7, #0xd]
	b _080D3D10
	.align 2, 0
_080D3CD4: .4byte 0xFFFF6000
_080D3CD8: .4byte 0x00000101
_080D3CDC: .4byte wStaticGraphicTilenums
_080D3CE0: .4byte 0x000003CE
_080D3CE4: .4byte wStaticMotionPalIDs
_080D3CE8: .4byte 0x000003AF
_080D3CEC: .4byte gStaticMotionGraphics
_080D3CF0: .4byte gStaticMotionGraphics+12
_080D3CF4: .4byte RNG_0202f388
_080D3CF8: .4byte 0xFFFFC000
_080D3CFC: .4byte 0x000343FD
_080D3D00: .4byte 0x00269EC3
_080D3D04: .4byte pZero2
_080D3D08:
	ldr r0, _080D3D4C @ =pZero2
	ldr r1, [r0]
	ldr r0, [r7, #0x64]
	str r0, [r1, #0x58]
_080D3D10:
	ldrb r0, [r7, #0xd]
	cmp r0, #2
	bhi _080D3D3A
	ldrb r0, [r7, #0x12]
	adds r0, #1
	strb r0, [r7, #0x12]
	movs r1, #1
	ands r0, r1
	cmp r0, #0
	bne _080D3D30
	movs r0, #4
	movs r1, #0
	movs r2, #0
	movs r3, #0
	bl FUN_080c5628
_080D3D30:
	adds r1, r7, #0
	adds r1, #0x54
	movs r0, #2
	bl AppendQuake
_080D3D3A:
	add sp, #8
	pop {r3, r4, r5}
	mov r8, r3
	mov sb, r4
	mov sl, r5
	pop {r4, r5, r6, r7}
	pop {r0}
	bx r0
	.align 2, 0
_080D3D4C: .4byte pZero2

	thumb_func_start Actor31_Update
Actor31_Update: @ 0x080D3D50
	push {r4, r5, lr}
	adds r4, r0, #0
	ldrb r5, [r4, #0xd]
	cmp r5, #1
	beq _080D3D98
	cmp r5, #1
	bgt _080D3DD8
	cmp r5, #0
	bne _080D3DD8
	ldrb r1, [r4, #0xa]
	movs r0, #0xfe
	ands r0, r1
	strb r0, [r4, #0xa]
	adds r0, r4, #0
	adds r0, #0x54
	movs r1, #1
	movs r2, #0
	bl CreateVFX39
	str r0, [r4, #0x28]
	adds r0, #0x7c
	strb r5, [r0]
	ldr r0, [r4, #0x28]
	adds r0, #0x74
	movs r1, #0x1f
	strb r1, [r0]
	ldr r0, [r4, #0x28]
	adds r0, #0x75
	strb r1, [r0]
	ldr r0, [r4, #0x28]
	adds r0, #0x76
	strb r1, [r0]
	strb r5, [r4, #0x12]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D3D98:
	ldrb r0, [r4, #0x12]
	adds r0, #1
	strb r0, [r4, #0x12]
	ldr r3, [r4, #0x28]
	ldr r2, _080D3DE0 @ =gSineTable
	movs r1, #0xfe
	ands r0, r1
	adds r0, r0, r2
	movs r2, #0
	ldrsh r1, [r0, r2]
	lsls r0, r1, #1
	adds r0, r0, r1
	lsls r0, r0, #7
	str r0, [r3, #0x78]
	ldr r2, [r4, #0x28]
	ldrb r0, [r4, #0x12]
	movs r3, #1
	adds r1, r3, #0
	ands r1, r0
	lsls r1, r1, #0xc
	ldr r0, [r2, #0x78]
	adds r0, r0, r1
	str r0, [r2, #0x78]
	ldrb r0, [r4, #0x12]
	cmp r0, #0x81
	bne _080D3DD8
	ldr r0, [r4, #0x28]
	adds r0, #0x77
	strb r3, [r0]
	ldrb r0, [r4, #0xd]
	adds r0, #1
	strb r0, [r4, #0xd]
_080D3DD8:
	pop {r4, r5}
	pop {r0}
	bx r0
	.align 2, 0
_080D3DE0: .4byte gSineTable
