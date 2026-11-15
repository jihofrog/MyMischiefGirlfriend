// Race3D v3b experiment: copy of MMG/Character/ToonHair whose colour pass writes stencil 1 on visible hair pixels
// (the brow card of MMG/Experiments/BrowCard draws only there). Draw it after the head (queue 2010).
// hair_bob_01: Unity side of the Blender M_hair_bob_01_01 material.
// Toon ramp x hair colour x baked AO (vertex colour R), thin strand streaks from the angle around the hair axis,
// and a soft highlight band at the upper head broken up by the same streaks (lit side, facing the viewer).
// Object space of the FBX: X = -Blender x, Y = Blender z, Z = -Blender y. Light direction comes from _LightDir.
Shader "MMG/Experiments/ToonHairStencil"
{
    Properties
    {
        _HairColor ("Hair colour", Color) = (0.487, 0.266, 0.233, 1)
        _LightScale ("Lambert scale (Blender sun 3.0)", Float) = 0.76
        _Ambient ("Ambient", Float) = 0.05
        _AOMin ("AO floor", Range(0, 1)) = 0.55
        _AxisY ("Hair axis (Blender y)", Float) = 0.02
        _StreakFreq ("Streaks per radian", Float) = 38
        _StreakSlant ("Streak slant per metre", Float) = 6
        _StreakDark ("Streak darkening", Range(0, 0.5)) = 0.12
        _BandZ ("Highlight height (m)", Float) = 1.565
        _BandJitter ("Highlight jitter (m)", Float) = 0.018
        _BandIn ("Highlight inner half width", Float) = 0.003
        _BandOut ("Highlight outer half width", Float) = 0.014
        _BandStrength ("Highlight strength", Range(0, 1)) = 0.5
        _LightDir ("Light direction (world)", Vector) = (-0.3, 0.8, -0.5, 0)
        _OutlineColor ("Outline", Color) = (0.26, 0.12, 0.1, 1)
        _OutlineWidth ("Outline width (m)", Float) = 0.001
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" "Queue" = "Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            half4 _HairColor, _OutlineColor;
            float _LightScale, _Ambient, _AOMin, _AxisY, _StreakFreq, _StreakSlant, _StreakDark;
            float _BandZ, _BandJitter, _BandIn, _BandOut, _BandStrength, _OutlineWidth;
            float4 _LightDir;
        CBUFFER_END
        ENDHLSL

        Pass
        {
            Name "Toon"
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            Stencil { Ref 1 Comp Always Pass Replace }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; half4 color : COLOR; };
            struct V { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; float3 viewWS : TEXCOORD1; float3 posOS : TEXCOORD2; half4 color : COLOR; };
            V vert(A i)
            {
                V o;
                VertexPositionInputs p = GetVertexPositionInputs(i.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.viewWS = GetWorldSpaceViewDir(p.positionWS);
                o.posOS = i.positionOS.xyz; o.color = i.color;
                return o;
            }
            float Ramp(float l)
            {
                if (l < 0.30) return 0.5;
                if (l < 0.40) return lerp(0.5, 0.8, (l - 0.30) / 0.10);
                if (l < 0.60) return lerp(0.8, 1.0, (l - 0.40) / 0.20);
                if (l < 0.68) return lerp(1.0, 1.22, (l - 0.60) / 0.08);
                return 1.22;
            }
            float Hash(float n) { return frac(sin(n * 12.9898) * 43758.5453); }
            float Noise1(float w)
            {
                float i = floor(w), f = frac(w);
                float u = f * f * (3 - 2 * f);
                return lerp(Hash(i), Hash(i + 1), u);
            }
            float Fbm(float w)
            {
                float s = 0, a = 0.5, n = 0;
                for (int k = 0; k < 4; k++) { s += Noise1(w) * a; n += a; w = w * 2.0 + 17.0; a *= 0.55; }
                return s / n;
            }
            half4 frag(V i) : SV_Target
            {
                float3 n = normalize(i.normalWS);
                float l = _LightScale * saturate(dot(n, normalize(_LightDir.xyz))) + _Ambient;
                half3 col = _HairColor.rgb * Ramp(l);
                col *= lerp(_AOMin, 1.0, i.color.r);
                float bx = -i.posOS.x, by = -i.posOS.z, bz = i.posOS.y;            // back to Blender axes
                float ang = atan2(bx, _AxisY - by);
                float s = saturate((Fbm(ang * _StreakFreq + bz * _StreakSlant) - 0.32) / 0.36);
                col *= (1 - _StreakDark) + _StreakDark * s;
                float d = abs(bz - (_BandZ - _BandJitter * (s - 0.5)));
                float band = saturate((_BandOut - d) / (_BandOut - _BandIn));
                float lit = saturate((l - 0.42) / 0.18);
                float facing = saturate(dot(n, normalize(i.viewWS)));
                col = lerp(col, lerp(_HairColor.rgb, 1, 0.45), band * lit * facing * (0.35 + 0.65 * s) * _BandStrength);
                return half4(col, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "Outline"
            Tags { "LightMode" = "SRPDefaultUnlit" }
            Cull Front
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct V { float4 positionCS : SV_POSITION; };
            V vert(A i)
            {
                V o;
                float3 ws = TransformObjectToWorld(i.positionOS.xyz) + TransformObjectToWorldNormal(i.normalOS) * _OutlineWidth;
                o.positionCS = TransformWorldToHClip(ws);
                return o;
            }
            half4 frag(V i) : SV_Target { return _OutlineColor; }
            ENDHLSL
        }
    }
}
